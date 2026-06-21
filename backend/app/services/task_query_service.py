from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

# ==============================================================================
# PHASE 4: TASK QUERY SERVICE
# Dịch vụ này chứa các hàm truy vấn trực tiếp vào CSDL để lấy danh sách task cụ thể.
# Mục đích: Làm "vũ khí" cho Chatbot. Khi Chatbot phát hiện người dùng đang hỏi về 
# một chủ đề cụ thể (ví dụ: task trễ hạn, task bị chặn), nó sẽ gọi các hàm này 
# để lấy đúng dữ liệu đó nhét vào Prompt cho AI.
# ==============================================================================

def get_overdue_tasks(db, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các task đã quá hạn (due_date < hôm nay) và chưa hoàn thành.
    Giới hạn mặc định là 20 task để tránh làm tràn bộ nhớ (Token) của AI.
    """
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, title, status, priority, due_date
            FROM tasks
            WHERE project_id = %s
              AND due_date < CURRENT_DATE
              AND status != 'done'
            ORDER BY due_date ASC
            LIMIT %s
        """, (project_id, limit))
        return cur.fetchall()
    finally:
        cur.close()

def get_blocked_tasks(db, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các task đang bị chặn (status = 'blocked').
    """
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, title, status, priority, due_date
            FROM tasks
            WHERE project_id = %s AND status = 'blocked'
            ORDER BY created_at DESC
            LIMIT %s
        """, (project_id, limit))
        return cur.fetchall()
    finally:
        cur.close()

def get_tasks_by_assignee(db, project_id: str, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các task đang được giao cho một người cụ thể (dựa vào user_id).
    Hàm này join với bảng users để lấy luôn tên người phụ trách.
    """
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.id, t.title, t.status, t.priority, t.due_date, u.full_name as assignee_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            WHERE t.project_id = %s AND t.assignee_id = %s
            ORDER BY t.created_at DESC
            LIMIT %s
        """, (project_id, user_id, limit))
        return cur.fetchall()
    finally:
        cur.close()

def get_tasks_by_priority(db, project_id: str, priority: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các task theo độ ưu tiên (high, medium, low).
    """
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, title, status, priority, due_date
            FROM tasks
            WHERE project_id = %s AND priority = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (project_id, priority, limit))
        return cur.fetchall()
    finally:
        cur.close()

def get_tasks_by_status(db, project_id: str, status: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các task theo trạng thái (todo, in_progress, review, done).
    """
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, title, status, priority, due_date
            FROM tasks
            WHERE project_id = %s AND status = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (project_id, status, limit))
        return cur.fetchall()
    finally:
        cur.close()
