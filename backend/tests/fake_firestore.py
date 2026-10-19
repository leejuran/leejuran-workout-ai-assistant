"""테스트용 in-memory Firestore 흉내.
실제 firebase_admin.firestore 클라이언트의 사용 패턴
(collection().document().set/get/update/delete, order_by, limit, stream, batch)만
이 프로젝트가 쓰는 범위 내에서 재현한다.
"""

import itertools


class FakeDocSnapshot:
    def __init__(self, doc_id, data, exists):
        self.id = doc_id
        self._data = data
        self.exists = exists

    def to_dict(self):
        return dict(self._data) if self._data else {}


class FakeDocRef:
    def __init__(self, store, doc_id):
        self._store = store
        self.id = doc_id

    def set(self, data):
        self._store[self.id] = dict(data)

    def update(self, patch):
        self._store[self.id].update(patch)

    def get(self):
        exists = self.id in self._store
        return FakeDocSnapshot(self.id, self._store.get(self.id), exists)

    def delete(self):
        self._store.pop(self.id, None)


class FakeQuery:
    def __init__(self, store, order_field=None, reverse=False, limit_n=None):
        self._store = store
        self._order_field = order_field
        self._reverse = reverse
        self._limit_n = limit_n

    def order_by(self, field, direction="ASCENDING"):
        return FakeQuery(self._store, field, direction == "DESCENDING", self._limit_n)

    def limit(self, n):
        return FakeQuery(self._store, self._order_field, self._reverse, n)

    def stream(self):
        items = [FakeDocSnapshot(k, v, True) for k, v in self._store.items()]
        if self._order_field:
            items.sort(key=lambda d: d.to_dict().get(self._order_field, ""), reverse=self._reverse)
        if self._limit_n:
            items = items[: self._limit_n]
        return items


class FakeCollection(FakeQuery):
    def __init__(self, store, id_counter):
        super().__init__(store)
        self._id_counter = id_counter

    def document(self, doc_id=None):
        if doc_id is None:
            doc_id = f"auto-{next(self._id_counter)}"
        return FakeDocRef(self._store, doc_id)


class FakeBatch:
    def __init__(self):
        self._ops = []

    def set(self, doc_ref, data):
        self._ops.append((doc_ref, data))

    def commit(self):
        for doc_ref, data in self._ops:
            doc_ref.set(data)
        self._ops = []


class FakeFirestoreClient:
    """DATA_COLLECTION, CONVERSATIONS_COLLECTION 등 컬렉션 이름별로 독립된 저장소를 유지."""

    def __init__(self):
        self._collections = {}
        self._id_counters = {}

    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = {}
            self._id_counters[name] = itertools.count(1)
        return FakeCollection(self._collections[name], self._id_counters[name])

    def batch(self):
        return FakeBatch()
