from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException

from app.firestore_client import CONVERSATIONS_COLLECTION, get_firestore_client
from app.models import ConversationIn, ConversationOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@router.post("", response_model=ConversationOut)
def create_conversation(payload: ConversationIn):
    db = get_firestore_client()
    doc_ref = db.collection(CONVERSATIONS_COLLECTION).document()
    data = {
        "title": payload.title,
        "messages": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    doc_ref.set(data)
    return ConversationOut(id=doc_ref.id, **data)


@router.get("", response_model=List[ConversationOut])
def list_conversations():
    db = get_firestore_client()
    docs = (
        db.collection(CONVERSATIONS_COLLECTION)
        .order_by("updated_at", direction="DESCENDING")
        .stream()
    )
    return [ConversationOut(id=d.id, **d.to_dict()) for d in docs]


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str):
    db = get_firestore_client()
    doc = db.collection(CONVERSATIONS_COLLECTION).document(conversation_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return ConversationOut(id=doc.id, **doc.to_dict())


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(CONVERSATIONS_COLLECTION).document(conversation_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    doc_ref.delete()
    return {"status": "deleted", "id": conversation_id}
