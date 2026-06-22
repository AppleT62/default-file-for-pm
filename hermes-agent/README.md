# 헤르메스 에이전트 (Hermes Agent) — 24시간 무인 AI 비서

Claude API + 텔레그램 + VPS + PM2 + SQLite로 구성한 개인용 자율 에이전트.
이 디렉터리 안의 코드가 실제로 동작하는 최소 구현체입니다. 아래 순서대로 따라 하면 됩니다.

```
hermes-agent/
├── README.md              ← 이 문서 (전체 가이드)
├── setup.sh                ← ② 서버 환경 자동 설치 스크립트
├── ecosystem.config.js    ← ⑤ PM2 실행 설정
├── requirements.txt        ← Python 의존성 목록
├── .env.example             ← 환경변수 템플릿 (복사해서 .env로 사용)
├── src/
│   ├── config.py            ← .env 값을 읽어 전역 설정으로 노출
│   ├── memory.py            ← ④ SQLite 기반 대화/선호도 영구 저장
│   ├── skills.py             ← ④ 마크다운 스킬 문서 저장/조회
│   ├── agent_core.py         ← ③ Claude API 호출 + 도구 실행 루프 (에이전트 두뇌)
│   ├── telegram_bot.py       ← ③ 텔레그램 메시지 수신/응답
│   ├── jobs.py                ← 사용자가 직접 채워 넣는 예약 작업(크론) 목록
│   ├── scheduler.py           ← ①/⑤ APScheduler로 크론 작업을 깨워 선제 메시지 발송
│   └── main.py                 ← 전체 기동 진입점 (pm2가 이 파일을 실행)
├── skills/                  ← 에이전트가 스스로 작성한 스킬 .md 파일들이 쌓이는 곳
├── data/memory.db            ← 대화 이력 + 선호도 SQLite DB (gitignore됨)
└── logs/                      ← pm2 표준출력/에러 로그
```

---

## ① 전체 아키텍처

```
[갤럭시탭/아이패드]
   │ SSH(Termius/Termux) — 서버 관리용
   │ Telegram App        — 실제 대화용
   ▼
[VPS: Ubuntu 22.04] ── pm2(상시 프로세스 관리) ── src/main.py
                                  │
                  ┌───────────────┼────────────────┐
                  ▼               ▼                ▼
          telegram_bot.py   scheduler.py      agent_core.py
        (사용자 메시지 수신)  (크론으로 선제   (Claude API 호출 +
                              메시지 발송)      도구 실행 루프)
                                  │                 │
                                  └────────┬────────┘
                                           ▼
                          ┌────────────────┴────────────────┐
                          ▼                                 ▼
                  memory.py (SQLite)                 skills.py (Markdown)
              대화 이력 + 사용자 선호도              자동 생성된 재사용 스킬
```

핵심 설계 포인트:

- **무인 자동화**: `scheduler.py`가 `jobs.py`에 정의된 크론 표현식대로 깨어나 `agent_core.run_turn()`을 호출하고, 결과를 텔레그램으로 먼저 보낸다. 사용자가 기기를 꺼둬도 VPS가 계속 돈다.
- **다중 채널**: 지금은 텔레그램만 구현했지만 `telegram_bot.py`와 같은 패턴으로 `slack_bot.py`를 추가하고 `main.py`에서 같은 `agent_core.run_turn()`을 공유하면 슬랙도 동일하게 붙는다.
- **지속적 메모리**: 매 턴마다 `memory.add_message()`로 대화를 SQLite에 적재하고, 다음 호출 시 `memory.recent_messages()`로 최근 N개를 다시 컨텍스트에 넣는다. 사용자 선호(보고서 서식, 말투 등)는 별도 `preferences` 테이블에 key-value로 누적 저장된다.
- **자동 스킬 생성**: Claude에게 `save_skill` 도구를 주고, "복잡한 작업을 성공적으로 끝내면 스스로 문서화하라"는 지시를 시스템 프롬프트에 넣었다. 모델이 알아서 적절한 시점에 도구를 호출해 `skills/*.md`를 생성한다. 다음 턴부터는 시스템 프롬프트에 스킬 목록이 자동으로 포함되어 재사용된다.
- **도구(Tools)**: `remember_preference`, `save_skill`, `read_skill`, `run_shell` 네 가지를 기본 제공. `run_shell`은 서버 자체에서 명령을 실행할 수 있어 강력하지만 위험하므로, 시스템 프롬프트에서 "파괴적 명령은 사용자 확인 후 실행"하도록 지시해 두었다. 필요하면 `agent_core.TOOLS`에 도구를 더 추가하면 된다.

---

## ② Ubuntu 22.04 서버 환경 준비

VPS(Vultr/DigitalOcean 등)를 만들고 SSH로 접속한 뒤:

```bash
git clone <이 저장소 주소> hermes-agent
cd hermes-agent/hermes-agent
chmod +x setup.sh
./setup.sh
```

`setup.sh`가 하는 일 (수동으로도 동일하게 실행 가능):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip sqlite3 build-essential

# Node.js 20 LTS + PM2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# Python 가상환경
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

---

## ③ 텔레그램 ↔ Claude API 연동 코드

1. 텔레그램에서 **@BotFather**에게 `/newbot`으로 봇을 만들고 토큰을 받는다.
2. 본인의 텔레그램 사용자 ID는 **@userinfobot**에게 말을 걸면 알려준다.
3. `.env` 작성:

```bash
cp .env.example .env
nano .env
```

```
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_ALLOWED_USER_IDS=본인텔레그램ID
```

핵심 코드는 `src/agent_core.py`(Claude 호출 + 도구 루프)와 `src/telegram_bot.py`(메시지 수신)에 있다. 동작 원리:

1. 사용자가 텔레그램으로 메시지를 보내면 `telegram_bot._on_message`가 받는다.
2. `TELEGRAM_ALLOWED_USER_IDS`에 없는 사람은 무시한다 (봇이 공개되어도 타인이 못 씀).
3. `agent_core.run_turn(user_id, text)`가 호출되어:
   - SQLite에서 최근 대화 이력을 불러오고,
   - 사용자 선호/저장된 스킬 목록을 시스템 프롬프트에 주입한 뒤,
   - Claude API를 호출한다.
   - 모델이 도구(`tool_use`)를 요청하면 실행하고 결과를 다시 모델에 돌려주는 루프를 최대 8회 반복한다.
4. 최종 텍스트를 SQLite에 저장하고 텔레그램으로 답장한다.

로컬에서 테스트:

```bash
source venv/bin/activate
python -m src.main
```

텔레그램 앱에서 봇에게 말을 걸어보면 바로 응답이 온다.

---

## ④ 영구 저장 구조 (SQLite + Markdown)

`src/memory.py`가 만드는 스키마:

```sql
conversations(id, user_id, role, content, created_at)   -- 대화 이력
preferences(user_id, key, value, updated_at)              -- 누적되는 선호/스타일
```

- 대화 이력은 `recent_messages(user_id, limit=20)`으로 최근 N개만 불러와 컨텍스트 길이를 제어한다.
- 선호도는 모델이 `remember_preference` 도구를 호출할 때마다 upsert된다. 예: `report_format = "불릿포인트, 3줄 이내"`.

`src/skills.py`는 스킬을 DB가 아니라 **마크다운 파일**(`skills/*.md`)로 저장한다. 사람이 직접 읽고 수정하기 쉽게 하기 위한 의도적 선택이다. 형식:

```markdown
# 스킬 제목

- 생성일: 2026-06-22 10:00

## 요약
한두 문장 요약

## 단계
1. ...
2. ...
```

`list_skills()`가 매 턴 시스템 프롬프트에 스킬 목록(제목+요약)을 넣어주고, 모델이 필요하면 `read_skill` 도구로 전체 내용을 불러와 그대로 따라간다.

DB/스킬 파일은 둘 다 깃에 커밋하지 않는다(`.gitignore` 처리). 서버에서만 누적되는 개인 데이터이기 때문이다.

---

## ⑤ PM2로 24시간 상시 실행

```bash
cd hermes-agent/hermes-agent
pm2 start ecosystem.config.js
pm2 save                     # 현재 프로세스 목록을 저장
pm2 startup                  # 서버 재부팅 시 pm2 자체가 자동 기동되도록 등록 (출력된 명령을 한 번 더 실행)
```

자주 쓰는 명령:

```bash
pm2 status                   # 실행 상태 확인
pm2 logs hermes-agent        # 실시간 로그
pm2 restart hermes-agent     # 코드 수정 후 재시작
pm2 stop hermes-agent        # 정지
```

`ecosystem.config.js`는 `venv/bin/python3 -m src.main`을 실행하며, 프로세스가 죽으면 5초 후 자동 재시작(`autorestart`)하고, 표준출력/에러를 `logs/out.log`, `logs/error.log`에 남긴다.

태블릿에서는 Termius(iPad) 또는 Termux(Galaxy Tab)로 SSH 접속해 위 pm2 명령만 가끔 확인하면 되고, 실제 대화는 텔레그램 앱으로 한다.

---

## 다음에 직접 추가해볼 만한 것

- `src/jobs.py`에 본인의 크론 작업(아침 브리핑, 정기 리포트 등)을 채워 넣기.
- 슬랙도 쓰고 싶다면 `telegram_bot.py`를 본떠 `slack_bot.py`를 만들고 `agent_core.run_turn()`을 그대로 재사용.
- `run_shell` 도구가 부담스럽다면 `agent_core.TOOLS`에서 제거하거나 화이트리스트 명령만 허용하도록 제한.
