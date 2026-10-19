from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException

from app.firestore_client import DATA_COLLECTION, get_firestore_client
from app.models import SummaryOut, WorkoutRecordIn, WorkoutRecordOut, WorkoutRecordUpdate

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=WorkoutRecordOut)
def create_record(record: WorkoutRecordIn):
    db = get_firestore_client()
    doc_ref = db.collection(DATA_COLLECTION).document()
    doc_ref.set(record.model_dump())
    return WorkoutRecordOut(id=doc_ref.id, **record.model_dump())


@router.get("", response_model=List[WorkoutRecordOut])
def list_records(limit: int = 500):
    db = get_firestore_client()
    docs = (
        db.collection(DATA_COLLECTION)
        .order_by("date")
        .limit(limit)
        .stream()
    )
    return [WorkoutRecordOut(id=d.id, **d.to_dict()) for d in docs]


@router.put("/{record_id}", response_model=WorkoutRecordOut)
def update_record(record_id: str, update: WorkoutRecordUpdate):
    db = get_firestore_client()
    doc_ref = db.collection(DATA_COLLECTION).document(record_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")

    patch = {k: v for k, v in update.model_dump().items() if v is not None}
    doc_ref.update(patch)
    merged = {**doc.to_dict(), **patch}
    return WorkoutRecordOut(id=record_id, **merged)


@router.delete("/{record_id}")
def delete_record(record_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(DATA_COLLECTION).document(record_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    doc_ref.delete()
    return {"status": "deleted", "id": record_id}


@router.get("/summary", response_model=SummaryOut)
def get_summary():
    """전체 운동 기록을 집계해 GPT 시스템 프롬프트에 주입할 요약을 만든다."""
    db = get_firestore_client()
    docs = list(db.collection(DATA_COLLECTION).order_by("date").stream())

    if not docs:
        return SummaryOut(
            total_sessions=0,
            total_minutes=0,
            avg_minutes_per_session=0,
            sessions_last_7_days=0,
            sessions_last_30_days=0,
            avg_sessions_per_week=0,
            date_range={"start": None, "end": None},
        )

    records = [d.to_dict() for d in docs]
    total_sessions = len(records)
    total_minutes = sum(r.get("value", 0) for r in records)
    avg_minutes = total_minutes / total_sessions if total_sessions else 0

    today = date.today()
    dates = [datetime.strptime(r["date"], "%Y-%m-%d").date() for r in records]

    sessions_7 = sum(1 for d in dates if today - d <= timedelta(days=7))
    sessions_30 = sum(1 for d in dates if today - d <= timedelta(days=30))

    span_days = max((max(dates) - min(dates)).days, 1)
    avg_per_week = total_sessions / (span_days / 7)

    return SummaryOut(
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        avg_minutes_per_session=round(avg_minutes, 1),
        sessions_last_7_days=sessions_7,
        sessions_last_30_days=sessions_30,
        avg_sessions_per_week=round(avg_per_week, 1),
        date_range={"start": min(dates).isoformat(), "end": max(dates).isoformat()},
    )
