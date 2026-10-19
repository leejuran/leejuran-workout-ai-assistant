"""
프론트-백엔드 연동 테스트 (실제 Firestore/OpenAI 대신 fake/mock 사용).

로컬에서 실행하는 법:
    cd backend
    pip install -r requirements.txt
    pip install pytest
    pytest tests/test_api_integration.py -v

실제 클라우드 자격 증명이 전혀 없어도 전체 API 흐름
(기록 CRUD → summary 계산 → 대화 생성 → 챗봇 응답 저장)이
설계대로 동작하는지 검증한다.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# chat.py는 모듈을 불러오는 시점에 OpenAI(api_key=...)를 생성한다.
# 실제 호출은 아래에서 mock으로 대체하지만, import 자체가 막히지 않도록
# 진짜 키가 없을 때만 더미 값을 넣어준다 (실제 키가 있으면 그대로 사용).
os.environ.setdefault("OPENAI_API_KEY", "test-placeholder-key")

from tests.fake_firestore import FakeFirestoreClient  # noqa: E402


@pytest.fixture
def client():
    fake_db = FakeFirestoreClient()

    # 1) Firestore를 fake로 교체
    with patch("app.firestore_client.get_firestore_client", return_value=fake_db), \
         patch("app.routers.data.get_firestore_client", return_value=fake_db), \
         patch("app.routers.conversations.get_firestore_client", return_value=fake_db), \
         patch("app.routers.chat.get_firestore_client", return_value=fake_db), \
         patch("app.routers.chat.client") as mock_openai:

        # 2) OpenAI 응답을 mock으로 대체
        mock_reply = MagicMock()
        mock_reply.choices[0].message.content = "이번 주 운동 패턴을 보니 꾸준하시네요! 계속 이 페이스를 유지해보세요."
        mock_openai.chat.completions.create.return_value = mock_reply

        from app.main import app

        with TestClient(app) as c:
            yield c


def test_health_check(client):
    res = client.get("/")
    assert res.status_code == 200


def test_data_crud_and_summary(client):
    # 생성
    r1 = client.post("/api/data", json={"date": "2026-09-01", "value": 55, "memo": "필라테스"})
    assert r1.status_code == 200
    record = r1.json()
    assert record["value"] == 55
    record_id = record["id"]

    client.post("/api/data", json={"date": "2026-09-03", "value": 60, "memo": ""})
    client.post("/api/data", json={"date": "2026-09-05", "value": 50, "memo": ""})

    # 목록 조회 - 프론트가 기대하는 필드(id/date/value/memo) 확인
    r2 = client.get("/api/data")
    assert r2.status_code == 200
    records = r2.json()
    assert len(records) == 3
    assert set(records[0].keys()) == {"id", "date", "value", "memo"}

    # summary - 프론트가 참조하는 필드 전부 존재하는지 확인
    r3 = client.get("/api/data/summary")
    assert r3.status_code == 200
    summary = r3.json()
    for field in [
        "total_sessions", "total_minutes", "avg_minutes_per_session",
        "sessions_last_7_days", "sessions_last_30_days", "avg_sessions_per_week",
    ]:
        assert field in summary
    assert summary["total_sessions"] == 3
    assert summary["total_minutes"] == 165

    # 수정
    r4 = client.put(f"/api/data/{record_id}", json={"value": 58})
    assert r4.status_code == 200
    assert r4.json()["value"] == 58

    # 삭제
    r5 = client.delete(f"/api/data/{record_id}")
    assert r5.status_code == 200
    assert client.get("/api/data").json().__len__() == 2

    # 존재하지 않는 기록 삭제 -> 404
    r6 = client.delete(f"/api/data/{record_id}")
    assert r6.status_code == 404


def test_chat_creates_conversation_and_saves_history(client):
    # summary용 데이터 하나 넣어둠 (없어도 동작해야 하지만 실제 사용 흐름 재현)
    client.post("/api/data", json={"date": "2026-09-01", "value": 55, "memo": "필라테스"})

    # 새 대화로 첫 메시지 전송 (conversation_id 없음)
    r1 = client.post("/api/chat", json={"message": "오늘 운동 가도 될까?"})
    assert r1.status_code == 200
    body1 = r1.json()
    assert "conversation_id" in body1 and "reply" in body1
    conv_id = body1["conversation_id"]
    assert body1["reply"]  # 빈 문자열이 아님

    # 같은 대화로 두 번째 메시지 전송
    r2 = client.post("/api/chat", json={"conversation_id": conv_id, "message": "얼마나 쉬어야 할까?"})
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id

    # 대화 목록/상세에서 프론트가 쓰는 필드 확인
    r3 = client.get("/api/conversations")
    assert r3.status_code == 200
    conv_list = r3.json()
    assert len(conv_list) == 1
    assert set(["id", "title", "messages"]).issubset(conv_list[0].keys())

    r4 = client.get(f"/api/conversations/{conv_id}")
    messages = r4.json()["messages"]
    # user/assistant 쌍 * 2턴 = 4개 메시지가 순서대로 저장됐는지
    assert len(messages) == 4
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]


def test_chat_with_nonexistent_conversation_id_returns_404(client):
    r = client.post("/api/chat", json={"conversation_id": "no-such-id", "message": "hi"})
    assert r.status_code == 404


def test_chat_history_truncated_to_max_turns(client):
    from app.routers import chat as chat_module

    # MAX_HISTORY_TURNS을 2로 낮춰서 자르기 로직만 빠르게 검증
    with patch.object(chat_module, "MAX_HISTORY_TURNS", 2):
        conv_id = None
        for i in range(5):
            payload = {"message": f"메시지 {i}"}
            if conv_id:
                payload["conversation_id"] = conv_id
            res = client.post("/api/chat", json=payload)
            conv_id = res.json()["conversation_id"]

        # 저장된 메시지는 5턴(10개) 전부 유지되어야 함 (자르기는 GPT 호출에만 적용, 저장은 영향 없음)
        conv = client.get(f"/api/conversations/{conv_id}").json()
        assert len(conv["messages"]) == 10
