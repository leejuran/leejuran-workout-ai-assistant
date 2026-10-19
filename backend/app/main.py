import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, conversations, data

app = FastAPI(title="운동기록 AI 비서 API")

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "운동기록 AI 비서"}
