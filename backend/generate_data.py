"""
패턴 기반 운동기록 생성 스크립트
- 최근 6개월
- 평일(월~금) 중 주 4일 운동 (요일 무작위 선택, 매주 갱신)
- 회당 운동시간 50~60분 변동
- 운동 종류: 필라테스 (삼성헬스에 별도 기록은 없었으므로 패턴으로 생성)

출력: workout_seed_data.json
스키마: { date: "YYYY-MM-DD", value: 55, memo: "필라테스 ..." }
  - value = 운동 시간(분)
"""

import json
import random
from datetime import date, timedelta

random.seed(42)  # 재현 가능하도록 고정 (원하면 제거)

WEEKDAYS = [0, 1, 2, 3, 4]  # 월=0 ... 금=4
SESSIONS_PER_WEEK = 4
DURATION_RANGE = (50, 60)

MEMO_VARIANTS = [
    "필라테스 정규 수업 참여",
    "필라테스 - 코어 위주 루틴",
    "필라테스 - 스트레칭 비중 높음",
    "필라테스 - 컨디션 좋아서 강도 살짝 업",
    "필라테스 - 평소보다 살짝 피곤했음",
    "필라테스 개인 세션",
]


def daterange_last_months(months: int = 6):
    end = date.today()
    start = end - timedelta(days=30 * months)
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def generate_records(months: int = 6):
    all_days = daterange_last_months(months)

    # 주 단위로 그룹핑
    weeks = {}
    for d in all_days:
        year, week_num, _ = d.isocalendar()
        weeks.setdefault((year, week_num), []).append(d)

    records = []
    record_id = 1
    for _, days_in_week in weeks.items():
        weekday_candidates = [d for d in days_in_week if d.weekday() in WEEKDAYS]
        if not weekday_candidates:
            continue
        k = min(SESSIONS_PER_WEEK, len(weekday_candidates))
        chosen_days = sorted(random.sample(weekday_candidates, k))

        for d in chosen_days:
            duration = random.randint(*DURATION_RANGE)
            memo = random.choice(MEMO_VARIANTS)
            records.append(
                {
                    "id": f"seed-{record_id:04d}",
                    "date": d.isoformat(),
                    "value": duration,
                    "memo": memo,
                }
            )
            record_id += 1

    records.sort(key=lambda r: r["date"])
    return records


if __name__ == "__main__":
    data = generate_records(months=6)
    with open("workout_seed_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_sessions = len(data)
    total_minutes = sum(r["value"] for r in data)
    print(f"생성된 기록 수: {total_sessions}")
    print(f"총 운동 시간: {total_minutes}분 (~{total_minutes / 60:.1f}시간)")
    print("workout_seed_data.json 저장 완료")
