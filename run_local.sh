#!/bin/bash

# Hàm xử lý khi người dùng bấm Ctrl+C (Tắt server)
cleanup() {
    echo ""
    echo "Đang tắt các dịch vụ..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    echo "Đã tắt hoàn tất!"
    exit
}

# Gắn sự kiện Ctrl+C (SIGINT) vào hàm cleanup
trap cleanup SIGINT SIGTERM

echo "=================================================="
echo "🚀 Khởi động AI Project Management Copilot..."
echo "=================================================="

# 1. Khởi động Database (PostgreSQL)
echo "[1/3] Đang khởi động Database..."
cd backend
docker compose up -d
cd ..

# 2. Khởi động Backend (FastAPI)
echo "[2/3] Đang khởi động Backend API..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# 3. Khởi động Frontend (React/Vite)
echo "[3/3] Đang khởi động Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ MỌI THỨ ĐÃ SẴN SÀNG!"
echo "👉 Dashboard: http://localhost:5173/projects"
echo "👉 API Docs : http://localhost:8000/docs"
echo "--------------------------------------------------"
echo "Nhấn Ctrl + C để dừng tất cả dịch vụ."

# Lệnh này giữ cho script chạy liên tục để bạn có thể xem log của Frontend và Backend chung một cửa sổ
wait
