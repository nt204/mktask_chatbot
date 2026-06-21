from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.db.database import get_db
from app.core.security import get_current_user, check_project_access
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

# Định nghĩa cấu trúc dữ liệu người dùng sẽ gửi lên (Request Payload)
class ChatRequest(BaseModel):
    project_id: str
    message: str

@router.post("", response_model=Dict[str, Any])
def send_chat_message(
    request: ChatRequest, 
    db=Depends(get_db), 
    current_user=Depends(get_current_user)
):
    """
    Endpoint nhận tin nhắn từ giao diện, gọi AI và trả về kết quả.
    Lưu ý: Chúng ta phải gọi hàm check_project_access thủ công ở đây 
    để đảm bảo user có quyền truy cập project_id được gửi lên.
    """
    # 1. Kiểm tra quyền truy cập dự án
    check_project_access(request.project_id, current_user, db)
    
    # 2. Chuyển logic sang tầng Service để xử lý (gọi AI, lưu DB)
    try:
        response = chat_service.generate_chat_response(
            db=db,
            project_id=request.project_id,
            user_id=current_user['id'],
            user_message=request.message,
            user_role=current_user.get('project_role')
        )
        return response
    except Exception as e:
        # Bắt lỗi nếu có trục trặc trong lúc gọi AI
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/history", response_model=List[Dict[str, Any]])
def get_chat_history_api(
    project_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Endpoint lấy lịch sử chat của dự án để hiển thị lên frontend.
    """
    check_project_access(project_id, current_user, db)
    
    try:
        messages = chat_service.get_project_chat_history(db, project_id, current_user['id'])
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
