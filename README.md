# AI Project Management Copilot

Hệ thống Quản lý Dự án thông minh tích hợp **AI Copilot** giúp quản lý công việc, tự động hóa tương tác và hỏi đáp tài liệu dự án bằng công nghệ **RAG (Retrieval-Augmented Generation)** và **Tool Agent**.

---

## 🌟 Luồng Hoạt Động Cốt Lõi (Core Workflows)

### 1. Luồng Hỏi Đáp Thông Minh (Router & RAG)
Khi người dùng gửi tin nhắn (ví dụ: *"Tài liệu dự án quy định phân quyền thế nào?"*):
1. **Router (`chat_service.py`)**: AI phân tích ngữ cảnh (nhớ 10 tin nhắn gần nhất) để phân loại câu hỏi vào một trong 3 luồng:
   - `document_rag`: Truy vấn tài liệu PDF/Markdown.
   - `db_qa`: Truy vấn tiến độ, số liệu từ CSDL PostgreSQL.
   - `hybrid`: Kết hợp cả hai nguồn dữ liệu trên.
2. **Retrieval**: Dữ liệu được trích xuất (Từ Qdrant Vector DB hoặc PostgreSQL) và nạp vào Prompt cho Gemini.
3. **Generation**: Gemini tổng hợp và trả về câu trả lời tự nhiên cho người dùng kèm Nguồn tham chiếu (Sources).

### 2. Luồng Thực Thi Thao Tác (Action Agent & Human-in-the-loop)
Khi người dùng ra lệnh (ví dụ: *"Tạo task Code giao diện, ưu tiên high, giao cho Hoàng"*):
1. **Agentic Security Firewall**: Code Python kiểm tra ngay `X-User-Email` và Role của user. Nếu là `DEVELOPER` hoặc `QA`, AI sẽ từ chối thực hiện.
2. **Extraction (`task_agent.py`)**: AI được ép trả về định dạng JSON (Pydantic Schema) với các thông tin đã bóc tách:
   ```json
   {"title": "Code giao diện", "priority": "high", "assignee_hint": "Hoàng"}
   ```
3. **Action Preview**: Frontend nhận JSON và dựng thẻ UI (Card) để người dùng xem trước. Lúc này dữ liệu **chưa** được lưu.
4. **Auto-Match & Execution**: 
   - Người dùng bấm "Xác nhận Tạo".
   - Backend nhận API `POST /tasks`, chạy thuật toán quét tên `assignee_hint` ("Hoàng") để đối chiếu với danh sách thành viên dự án và tự động lấy `user_id`.
   - Lưu Task vào PostgreSQL.

---

## 🔐 Cơ Chế Phân Quyền (RBAC & Agentic Security)

Hệ thống hiện tại sử dụng cơ chế **Mock Login** thông qua Header `X-User-Email` để giả lập quá trình xác thực.

- **API Security**: Hàm `require_project_role(["PM", "ADMIN"])` được gắn trực tiếp vào các API thay đổi dữ liệu để chặn Hacker gọi trực tiếp từ Postman.
- **Agentic Security**: AI được cung cấp Role của người dùng đang chat. Nó nhận thức được quyền hạn và từ chối các yêu cầu vượt thẩm quyền bằng ngôn ngữ tự nhiên.

---

## 🔌 Danh Sách API (API Endpoints)

Base URL mặc định: `http://localhost:8000/api`

### 👤 Xác thực & Users (Mock)
- `GET /users`: Lấy danh sách toàn bộ người dùng trong hệ thống để test chức năng chuyển đổi tài khoản (User Switcher).

### 📂 Quản lý Dự Án (Projects)
- `GET /projects`: Lấy danh sách tất cả dự án mà người dùng hiện tại có quyền truy cập.
- `GET /projects/{project_id}`: Lấy chi tiết số liệu tổng quan của một dự án.
- `GET /projects/{project_id}/members`: Lấy danh sách thành viên dự án.
- `GET /projects/{project_id}/sprints`: Lấy danh sách Sprints (Chu kỳ phát triển).
- `GET /projects/{project_id}/risks`: Lấy danh sách rủi ro (Risk Events).

### 📋 Quản lý Công Việc (Tasks)
- `GET /projects/{project_id}/tasks`: Lấy danh sách toàn bộ task trong dự án.
- `POST /projects/{project_id}/tasks`: Tạo mới task. 
  - *Header yêu cầu: `X-User-Email`*
  - *Quyền yêu cầu: PM, TEAM_LEAD, ADMIN, DIRECTOR.*
  - *Body (JSON)*: `{"title": "Tên", "description": "", "priority": "high", "assignee_hint": "Tên người dùng"}`

### 🤖 AI Copilot (Chat)
- `GET /chat/{project_id}/history`: Tải lại lịch sử trò chuyện (tối đa 10 tin nhắn gần nhất kèm metadata Action Preview để không mất giao diện khi F5).
- `POST /chat`: Gửi tin nhắn mới cho AI.
  - *Header yêu cầu: `X-User-Email`*
  - *Body (JSON)*: `{"project_id": "...", "message": "Câu hỏi/lệnh..."}`

### 📄 Quản lý Tài Liệu & Vector DB
- `GET /projects/{project_id}/documents`: Lấy danh sách tài liệu đã Upload.
- `POST /projects/{project_id}/documents/upload`: Upload file (PDF, TXT, MD). Backend sẽ tự động *Chunking* và *Embedding* dữ liệu bằng Google Gemini rồi lưu vào **Qdrant Vector DB**.

---

## 🚀 Hướng Dẫn Chạy (Local Development)

1. Cài đặt các biến môi trường trong file `backend/.env`:
   - `DATABASE_URL`
   - `GEMINI_API_KEY`
2. Chạy script để khởi động toàn bộ Frontend, Backend và Qdrant Docker:
   ```bash
   chmod +x run_local.sh
   ./run_local.sh
   ```
3. Truy cập Frontend: `http://localhost:5173`
4. Truy cập Swagger API Docs: `http://localhost:8000/docs`
