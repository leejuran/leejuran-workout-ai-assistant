from typing import List, Optional

from pydantic import BaseModel, Field


class WorkoutRecordIn(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    value: float = Field(..., description="운동 시간(분) 등 수치 값")
    memo: Optional[str] = ""


class WorkoutRecordUpdate(BaseModel):
    date: Optional[str] = None
    value: Optional[float] = None
    memo: Optional[str] = None


class WorkoutRecordOut(WorkoutRecordIn):
    id: str


class SummaryOut(BaseModel):
    total_sessions: int
    total_minutes: float
    avg_minutes_per_session: float
    sessions_last_7_days: int
    sessions_last_30_days: int
    avg_sessions_per_week: float
    date_range: dict


class ChatMessageIn(BaseModel):
    conversation_id: Optional[str] = None
    message: str


class ChatMessageOut(BaseModel):
    conversation_id: str
    reply: str


class ConversationIn(BaseModel):
    title: Optional[str] = "새 대화"


class MessageEntry(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    title: str
    messages: List[MessageEntry] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
