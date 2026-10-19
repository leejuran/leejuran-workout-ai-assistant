"""
Firestore 클라이언트 초기화.

로컬/Render 배포 모두에서 아래 두 방식 중 하나로 인증합니다.
1) 환경변수 GOOGLE_APPLICATION_CREDENTIALS_JSON 에 서비스 계정 JSON 전체를 문자열로 넣기 (Render 권장)
2) GOOGLE_APPLICATION_CREDENTIALS 에 서비스 계정 json 파일 경로 지정 (로컬 개발 권장)
"""

import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

_app = None


def get_firestore_client():
    global _app
    if _app is None:
        cred_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        elif cred_path:
            cred = credentials.Certificate(cred_path)
        else:
            raise RuntimeError(
                "Firestore 인증 정보가 없습니다. "
                "GOOGLE_APPLICATION_CREDENTIALS_JSON 또는 GOOGLE_APPLICATION_CREDENTIALS 를 설정하세요."
            )

        _app = firebase_admin.initialize_app(cred)

    return firestore.client()


DATA_COLLECTION = "workout_data"
CONVERSATIONS_COLLECTION = "conversations"
