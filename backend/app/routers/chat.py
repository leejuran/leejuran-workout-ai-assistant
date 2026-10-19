import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.firestore_client import CONVERSATIONS_COLLECTION, get_firestore_client
from app.models import ChatMessageIn, ChatMessageOut
from app.routers.data import get_summary

router = APIRouter(prefix="/api/chat", tags=["chat"])

base_url = os.environ.get("OPENAI_BASE_URL")
if base_url:
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=base_url,
)
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_HISTORY_TURNS = 10  # 최근 N턴(=N*2 메시지)만 GPT에 전달


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_system_prompt(summary) -> str:
    return f"""당신은 사용자의 운동 기록을 잘 아는 개인 운동 코치 AI입니다.
아래는 사용자의 운동 데이터 요약입니다. 이 정보를 바탕으로 구체적이고 개인화된 조언을 하세요.
데이터에 없는 사실을 지어내지 말고, 필요하면 데이터가 부족하다고 솔직히 말하세요.

[운동 데이터 요약]
- 총 운동 세션 수: {summary.total_sessions}회
- 총 운동 시간: {summary.total_minutes}분
- 세션당 평균 시간: {summary.avg_minutes_per_session}분
- 최근 7일 세션 수: {summary.sessions_last_7_days}회
- 최근 30일 세션 수: {summary.sessions_last_30_days}회
- 주당 평균 세션 수: {summary.avg_sessions_per_week}회
- 기록 기간: {summary.date_range.get('start')} ~ {summary.date_range.get('end')}

톤: 친근하지만 전문적으로. 답변은 3~5문장 내외로 간결하게.
"""


@router.post("", response_model=ChatMessageOut)
def chat(payload: ChatMessageIn):
    db = get_firestore_client()

    # 1. 대화 불러오기 or 새로 생성
    if payload.conversation_id:
        doc_ref = db.collection(CONVERSATIONS_COLLECTION).document(payload.conversation_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        conv = doc.to_dict()
    else:
        doc_ref = db.collection(CONVERSATIONS_COLLECTION).document()
        conv = {"title": payload.message[:20], "messages": [], "created_at": _now_iso()}

    # 2. 운동 데이터 요약 조회 → 시스템 프롬프트 구성
    summary = get_summary()
    system_prompt = build_system_prompt(summary)

    # 3. 기존 대화 + 새 사용자 메시지로 GPT 호출
    history = conv.get("messages", [])
    recent_history = history[-MAX_HISTORY_TURNS * 2:]  # 오래된 메시지는 GPT 호출에서 제외 (저장은 그대로 유지)
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in recent_history:
        api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": payload.message})

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=api_messages,
        )
        reply = completion.choices[0].message.content or (
            "죄송해요, 응답을 생성하지 못했어요. 다시 한 번 질문해 주세요."
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GPT 호출 실패: {e}")

    # 4. 대화 자동 저장
    history.append({"role": "user", "content": payload.message, "timestamp": _now_iso()})
    history.append({"role": "assistant", "content": reply, "timestamp": _now_iso()})
    conv["messages"] = history
    conv["updated_at"] = _now_iso()
    doc_ref.set(conv)

    return ChatMessageOut(conversation_id=doc_ref.id, reply=reply)
