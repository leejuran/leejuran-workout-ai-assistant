"""workout_seed_data.json 을 Firestore workout_data 컬렉션에 업로드."""

import json

from app.firestore_client import DATA_COLLECTION, get_firestore_client

if __name__ == "__main__":
    with open("workout_seed_data.json", encoding="utf-8") as f:
        records = json.load(f)

    db = get_firestore_client()
    batch = db.batch()
    count = 0

    for r in records:
        seed_id = r.pop("id")
        doc_ref = db.collection(DATA_COLLECTION).document(seed_id)
        batch.set(doc_ref, r)
        count += 1
        if count % 400 == 0:  # Firestore batch 최대 500건 제한 대비
            batch.commit()
            batch = db.batch()

    batch.commit()
    print(f"{count}건 업로드 완료 -> Firestore '{DATA_COLLECTION}' 컬렉션")
