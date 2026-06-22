#!/usr/bin/env bash
# Ubuntu 22.04 LTS 기준 헤르메스 에이전트 서버 환경 구축 스크립트
set -euo pipefail

echo "=== 1. 패키지 목록 갱신 ==="
sudo apt update && sudo apt upgrade -y

echo "=== 2. 기본 도구 설치 (git, python3, sqlite3) ==="
sudo apt install -y git python3 python3-venv python3-pip sqlite3 build-essential

echo "=== 3. Node.js 20 LTS 설치 (NodeSource) ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

echo "=== 4. PM2 전역 설치 ==="
sudo npm install -g pm2

echo "=== 5. Python 가상환경 생성 및 의존성 설치 ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "=== 6. 데이터/로그 디렉터리 준비 ==="
mkdir -p data logs skills

echo "=== 7. .env 준비 ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "-> .env 파일을 생성했습니다. ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN 등을 채워주세요."
fi

echo "=== 완료 ==="
echo "다음 단계: .env 값을 채운 뒤 'pm2 start ecosystem.config.js' 로 실행하세요."
