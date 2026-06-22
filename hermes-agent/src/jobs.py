"""사용자가 직접 편집하는 예약 작업(크론) 목록.

각 항목: (cron 표현식, 대상 텔레그램 chat_id, 에이전트에게 보낼 프롬프트)
cron 표현식은 'minute hour day month day_of_week' 형식 (APScheduler CronTrigger.from_crontab과 동일).
"""

JOBS = [
    # 매일 오전 8시 브리핑 예시. chat_id는 본인 텔레그램 ID로 교체.
    # ("0 8 * * *", 111111111, "오늘 일정과 날씨, 주요 뉴스를 간단히 요약해서 브리핑해줘."),
]
