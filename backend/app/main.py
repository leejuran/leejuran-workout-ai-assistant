from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, conversations, data

app = FastAPI(title="운동기록 AI 비서 API")

# Vercel 프론트엔드 도메인으로 교체하세요 (배포 후)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 배포 시 ["https://your-app.vercel.app"] 로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "운동기록 AI 비서"}
