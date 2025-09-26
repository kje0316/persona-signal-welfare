#!/bin/bash

# 복지 서비스 전체 시스템 실행 스크립트
echo "🚀 복지 서비스 시스템을 시작합니다..."

# 백그라운드에서 백엔드 서버 시작
echo "📡 백엔드 API 서버 시작 (포트 8001)..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate project
python src/backend/welfare_service_api.py &
BACKEND_PID=$!

# 잠시 대기 (백엔드 시작 시간)
sleep 3

# 프론트엔드 서버 시작
echo "🖥️  프론트엔드 서버 시작 (포트 3000)..."
cd src/frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 시스템이 실행되었습니다!"
echo "📱 프론트엔드: http://localhost:3000"
echo "🔧 백엔드 API: http://localhost:8001"
echo ""
echo "종료하려면 Ctrl+C를 누르세요..."

# Ctrl+C 신호 처리
trap "echo '🛑 시스템을 종료합니다...'; kill $BACKEND_PID $FRONTEND_PID; exit 0" SIGINT

# 프로세스가 살아있는지 대기
wait