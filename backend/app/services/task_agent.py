import os
import json
from google import genai
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# 1. KHỞI TẠO AI CLIENT
# Lấy API Key từ biến môi trường (.env) và khởi tạo kết nối với Gemini.
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# 2. ĐỊNH NGHĨA KHUÔN MẪU DỮ LIỆU (TOOL SCHEMA)
# Đây là phần quan trọng nhất của Tool Agent. Ta dùng Pydantic để định nghĩa 
# cấu trúc JSON mong muốn. Các 'description' chính là prompt ẩn để hướng dẫn AI 
# cách trích xuất dữ liệu cho từng trường.
class CreateTaskPayload(BaseModel):
    title: str = Field(description="Tiêu đề ngắn gọn của task")
    description: Optional[str] = Field(description="Mô tả chi tiết công việc, nếu có", default="")
    assignee_hint: Optional[str] = Field(description="Tên hoặc từ khóa người được giao task, ví dụ: 'Nam', 'Hoàng', nếu có", default=None)
    priority: str = Field(description="Độ ưu tiên: low, medium, high, urgent", default="medium")

# 3. HÀM XỬ LÝ CHÍNH CỦA AGENT
def handle_task_action(db, project_id: str, session_id: str, user_message: str, chat_history: str, user_role: str = None) -> Dict[str, Any]:
    from app.services.chat_service import save_chat_message
    
    # [Bảo mật] 1. Agentic Security Firewall (Chặn cứng ở tầng code)
    if user_role in ['DEVELOPER', 'QA', 'GUEST', 'VIEWER']:
        answer_text = f"Xin lỗi, với vai trò là {user_role}, bạn không có thẩm quyền tạo Task trên dự án này. Vui lòng liên hệ PM hoặc Team Lead."
        save_chat_message(db, session_id, "assistant", answer_text, {"mode": "action"})
        return {"answer": answer_text, "sources": []}

    # Kiểm tra xem API Key đã được cấu hình chưa
    if not client:
        return {"answer": "Lỗi: Không có kết nối với AI.", "sources": []}
        
    # Xây dựng Prompt: Đóng vai AI, nhận ngữ cảnh (Lịch sử + Tin nhắn mới) và đưa ra các quy tắc ép buộc AI phải tuân theo.
    prompt = f"""Bạn là Task Agent trong hệ thống AI Project Management Copilot.
Nhiệm vụ của bạn là đọc yêu cầu của người dùng, phân tích và trích xuất dữ liệu để điền vào form tạo Task mới.

LỊCH SỬ TRÒ CHUYỆN:
{chat_history if chat_history else 'Chưa có lịch sử'}

YÊU CẦU TẠO TASK:
{user_message}

Quy tắc:
- Trích xuất ngắn gọn, chính xác.
- priority chỉ được phép mang giá trị: low, medium, high, urgent. Mặc định là medium.
- Nếu không nhắc đến tên người giao, để trống assignee_hint.
- VAI TRÒ CỦA NGƯỜI DÙNG: {user_role}. Nếu họ yêu cầu tạo task nhưng không đủ quyền, hãy từ chối. (Lưu ý: Chúng ta đã có tường lửa code chặn role yếu, nhưng bạn cũng cần nhận thức điều này để trả lời nhất quán).
"""

    try:
        # Gọi Google Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Model dùng cho các tác vụ nhanh, rẻ
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json", # Bắt buộc AI trả về JSON, không nói chữ luyên thuyên
                response_schema=CreateTaskPayload,     # Ép JSON phải tuân theo cấu trúc Pydantic đã định nghĩa ở trên
                temperature=0.1                        # Để temperature thấp (0.1) giúp AI trả lời rập khuôn, chính xác, ít "sáng tạo" sai lệch
            )
        )
        
        # Parse JSON trả về từ AI thành object (Dictionary) của Python
        payload = json.loads(response.text)
        
        
        # Câu trả lời dạng text hiển thị cho người dùng
        answer_text = "Tôi đã điền sẵn form tạo Task dựa trên yêu cầu của bạn. Vui lòng kiểm tra và xác nhận bên dưới."
        
        # Đóng gói dữ liệu để frontend có thể vẽ thẻ (Card) Action Preview
        action_preview_data = {
            "tool": "create_task_preview", # Tên tool để Frontend biết cần render giao diện gì
            "payload": payload             # Dữ liệu task AI vừa trích xuất
        }
        
        # 4. LƯU VÀO DATABASE VÀ TRẢ VỀ FRONTEND
        # Lưu vào lịch sử chat (kèm theo cả metadata action_preview để khi F5 trang vẫn giữ được thẻ tạo task)
        save_chat_message(db, session_id, "assistant", answer_text, {"mode": "action", "action_preview": action_preview_data})
        
        # Trả về kết quả cho Router (sau đó sẽ gửi qua API cho Frontend)
        return {
            "answer": answer_text,
            "action_preview": action_preview_data,
            "sources": []
        }
    except Exception as e:
        # Xử lý các lỗi có thể xảy ra (hết hạn mức API, lỗi parse JSON, v.v)
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            answer = "Hệ thống AI đang bị quá tải (Rate Limit). Vui lòng thử lại sau 1 phút."
        else:
            answer = f"Lỗi khi trích xuất Task Payload: {error_msg}"
        return {"answer": answer, "sources": []}
