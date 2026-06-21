import os
import json
from google import genai
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Dict, Any, Literal, Optional, List
from pydantic import BaseModel, Field
from app.services import status_service, task_query_service, project_service, document_service

# Lấy API Key từ biến môi trường
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Bộ nhớ đệm cơ bản (In-Memory Cache) cho ứng dụng (SessionID + UserMessage) -> Result
EXACT_MATCH_CACHE = {}

class ChatRoute(BaseModel):
    mode: Literal["db_qa", "document_rag", "hybrid", "action", "clarification"]
    needs_database: bool
    needs_documents: bool
    needs_action: bool
    confidence: float = Field(ge=0, le=1)
    reason: str
    document_query: Optional[str] = None
    database_intent: Optional[str] = None
    required_tools: List[str] = []

ROUTER_PROMPT = """Bạn là Router cho AI Project Management Copilot.

Nhiệm vụ của bạn là phân loại câu hỏi người dùng để quyết định nguồn dữ liệu cần dùng.

Các mode:
- db_qa: hỏi dữ liệu hiện tại trong database như project, task, sprint, risk, assignee, deadline.
- document_rag: hỏi nội dung tài liệu, requirement, policy, quy trình, phân quyền được mô tả trong tài liệu.
- hybrid: cần cả tài liệu và dữ liệu hiện tại trong database.
- action: người dùng muốn tạo/sửa/xóa task, tạo report, tạo risk hoặc thực hiện thao tác.
- clarification: câu hỏi thiếu thông tin nghiêm trọng.

Quy tắc:
- Hãy đặc biệt chú ý đến LỊCH SỬ TRÒ CHUYỆN (Chat History) để phân giải các đại từ nhân xưng như "đó", "nó", "người đó", "các task này".
- Nếu câu hỏi hỏi "tài liệu nói gì", "theo requirement", "quy trình", "chính sách", "RBAC được mô tả" -> document_rag.
- Nếu câu hỏi hỏi "hiện tại", "task nào", "ai đang làm", "deadline", "status", "sprint tiến độ" -> db_qa.
- Nếu câu hỏi vừa hỏi quy định/tài liệu vừa hỏi tình trạng thực tế hiện tại -> hybrid.
- Nếu người dùng muốn tạo/sửa/cập nhật/xóa/generate report -> action.
- document_query là câu hỏi ĐƯỢC VIẾT LẠI (rewritten query) để tối ưu hóa tìm kiếm tài liệu (ví dụ: "sales executive quyền khách hàng RBAC")
- Không trả lời câu hỏi. Chỉ trả JSON theo schema.
"""

def get_chat_history(db, session_id: str, limit: int = 10) -> str:
    """Lấy 10 tin nhắn gần nhất trong phiên chat làm ngữ cảnh"""
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT role, content FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY created_at DESC LIMIT %s
        """, (session_id, limit))
        messages = cur.fetchall()
        if not messages:
            return ""
        # Reverse to get chronological order
        messages.reverse()
        history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in messages])
        return history_str
    except Exception as e:
        print(f"Error getting history: {e}")
        return ""
    finally:
        cur.close()

def route_message(message: str, project_id: str, user_id: str, chat_history: str) -> ChatRoute:
    if not client:
        return ChatRoute(mode="hybrid", needs_database=True, needs_documents=True, needs_action=False, confidence=1.0, reason="No AI client")
        
    try:
        prompt = ROUTER_PROMPT + f"\n\nLỊCH SỬ TRÒ CHUYỆN:\n{chat_history if chat_history else 'Chưa có lịch sử'}\n\nProject ID: {project_id}\nUser ID: {user_id}\nUser message: {message}"
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChatRoute,
                temperature=0.1
            )
        )
        route_dict = json.loads(response.text)
        route = ChatRoute(**route_dict)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"Routing error: 429 Rate Limit")
        else:
            print(f"Routing error: {error_msg}")
        route = ChatRoute(mode="hybrid", needs_database=True, needs_documents=True, needs_action=False, confidence=0.0, reason="Routing failed")

    if route.confidence < 0.65:
        route.mode = "hybrid"
        route.needs_database = True
        route.needs_documents = True
        route.reason = "Low router confidence, fallback to hybrid retrieval."

    return route

def get_or_create_session(db, project_id: str, user_id: str) -> str:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id FROM chat_sessions 
            WHERE project_id = %s AND user_id = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (project_id, user_id))
        session = cur.fetchone()
        
        if session:
            return session['id']
            
        cur.execute("""
            INSERT INTO chat_sessions (project_id, user_id, title)
            VALUES (%s, %s, %s) RETURNING id
        """, (project_id, user_id, "Project Copilot Chat"))
        new_session_id = cur.fetchone()['id']
        db.commit()
        return new_session_id
    finally:
        cur.close()

def get_project_chat_history(db, project_id: str, user_id: str) -> List[Dict[str, Any]]:
    session_id = get_or_create_session(db, project_id, user_id)
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT role, content, metadata, created_at 
            FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC
        """, (session_id,))
        messages = cur.fetchall()
        
        formatted_msgs = []
        for msg in messages:
            metadata = msg['metadata'] if msg['metadata'] else {}
            if msg['role'] == 'user':
                formatted_msgs.append({
                    "role": "user",
                    "content": msg['content']
                })
            else:
                formatted_msgs.append({
                    "role": "assistant",
                    "content": msg['content'],
                    "sources": metadata.get("sources", []),
                    "action_preview": metadata.get("action_preview", None)
                })
        return formatted_msgs
    finally:
        cur.close()

def save_chat_message(db, session_id: str, role: str, content: str, metadata: dict = None):
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO chat_messages (session_id, role, content, metadata)
            VALUES (%s, %s, %s, %s)
        """, (session_id, role, content, json.dumps(metadata or {})))
        db.commit()
    finally:
        cur.close()

def retrieve_document_evidence(project_id: str, query: str) -> Dict[str, Any]:
    doc_chunks = document_service.search_documents(project_id, query)
    if not doc_chunks:
        return {"context": "", "sources": []}
        
    context = "\n\n".join([
        f"[Source: {chunk.get('filename')} | Đoạn: {chunk.get('chunk_index')}]\n{chunk.get('text')}"
        for chunk in doc_chunks
    ])
    
    sources = [{
        "type": "document", 
        "id": chunk.get("document_id"), 
        "title": f"{chunk.get('filename')} (Đoạn {chunk.get('chunk_index')})"
    } for chunk in doc_chunks]
    
    return {"context": context, "sources": sources}

def retrieve_database_evidence(db, project_id: str, message: str) -> Dict[str, Any]:
    project_status = status_service.get_project_status(db, project_id)
    if not project_status:
        return {"context": "", "sources": []}
        
    msg_lower = message.lower()
    additional_context = {}
    sources = [{"type": "project_status", "id": project_status['project']['id'], "title": "Project Summary"}]
    
    if any(kw in msg_lower for kw in ["quá hạn", "trễ", "deadline"]):
        overdue_tasks = task_query_service.get_overdue_tasks(db, project_id)
        additional_context["overdue_tasks"] = overdue_tasks
        for t in overdue_tasks:
            sources.append({"type": "task", "id": t['id'], "title": t['title']})
            
    if any(kw in msg_lower for kw in ["blocked", "bị chặn", "bị kẹt"]):
        blocked_tasks = task_query_service.get_blocked_tasks(db, project_id)
        additional_context["blocked_tasks"] = blocked_tasks
        for t in blocked_tasks:
            sources.append({"type": "task", "id": t['id'], "title": t['title']})
            
    if "high" in msg_lower or "ưu tiên cao" in msg_lower:
        high_tasks = task_query_service.get_tasks_by_priority(db, project_id, "high")
        additional_context["high_priority_tasks"] = high_tasks
        for t in high_tasks:
            sources.append({"type": "task", "id": t['id'], "title": t['title']})

    members = project_service.get_project_members(db, project_id)
    for m in members:
        name_parts = m['full_name'].lower().split()
        if any(part in msg_lower for part in name_parts if len(part) > 2) or m['full_name'].lower() in msg_lower:
            user_tasks = task_query_service.get_tasks_by_assignee(db, project_id, m['id'])
            additional_context[f"tasks_of_{m['full_name']}"] = user_tasks
            for t in user_tasks:
                sources.append({"type": "task", "id": t['id'], "title": t['title']})

    unique_sources = []
    seen_ids = set()
    for s in sources:
        if s['id'] not in seen_ids:
            unique_sources.append(s)
            seen_ids.add(s['id'])
            
    context = f"DỮ LIỆU TỔNG QUAN DỰ ÁN:\n{json.dumps(project_status, ensure_ascii=False)}\n\nDỮ LIỆU CHI TIẾT TÌM ĐƯỢC:\n{json.dumps(additional_context, ensure_ascii=False, default=str)}"
    return {"context": context, "sources": unique_sources}

def answer_from_documents(db, project_id: str, session_id: str, user_message: str, route: ChatRoute, chat_history: str) -> Dict[str, Any]:
    query = route.document_query if route.document_query else user_message
    evidence = retrieve_document_evidence(project_id, query)
    
    if not evidence["context"]:
        answer = "Tôi chưa tìm thấy thông tin này trong tài liệu dự án."
        save_chat_message(db, session_id, "assistant", answer, {"mode": "document_rag", "query": query, "sources": []})
        return {"answer": answer, "sources": []}

    prompt = f"""Bạn là AI Copilot cho hệ thống CRM Internal System.
    
LỊCH SỬ TRÒ CHUYỆN:
{chat_history if chat_history else 'Chưa có lịch sử'}

Chỉ trả lời dựa trên CONTEXT bên dưới.
Nếu CONTEXT không có thông tin, hãy nói: "Tôi chưa tìm thấy thông tin này trong tài liệu dự án."
Không được bịa. Trả lời bằng tiếng Việt, rõ ràng.

CONTEXT:
{evidence['context']}

CÂU HỎI MỚI:
{user_message}
"""

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        ai_answer = response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            ai_answer = "Hệ thống AI đang bị quá tải do hết hạn ngạch API (Rate Limit). Vui lòng đợi khoảng 1 phút rồi thử lại nhé!"
        else:
            ai_answer = f"Lỗi khi kết nối với AI: {error_msg}"
        
    save_chat_message(db, session_id, "assistant", ai_answer, {"mode": "document_rag", "query": query, "sources": evidence["sources"]})
    return {"answer": ai_answer, "sources": evidence["sources"]}

def answer_from_database(db, project_id: str, session_id: str, user_message: str, route: ChatRoute, chat_history: str) -> Dict[str, Any]:
    evidence = retrieve_database_evidence(db, project_id, user_message)

    prompt = f"""Bạn là AI Project Management Copilot.

LỊCH SỬ TRÒ CHUYỆN:
{chat_history if chat_history else 'Chưa có lịch sử'}
    
{evidence['context']}
    
Quy tắc bắt buộc:
1. CHỈ trả lời dựa trên dữ liệu project được cung cấp ở trên.
2. KHÔNG BAO GIỜ bịa số liệu.
3. ĐỐI VỚI CÁC TASK: Hãy nhắc đến Tên Task trong câu trả lời.

CÂU HỎI MỚI: {user_message}
"""

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        ai_answer = response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            ai_answer = "Hệ thống AI đang bị quá tải do hết hạn ngạch API (Rate Limit). Vui lòng đợi khoảng 1 phút rồi thử lại nhé!"
        else:
            ai_answer = f"Lỗi khi kết nối với AI: {error_msg}"
        
    save_chat_message(db, session_id, "assistant", ai_answer, {"mode": "db_qa", "sources": evidence["sources"]})
    return {"answer": ai_answer, "sources": evidence["sources"]}

def answer_hybrid(db, project_id: str, session_id: str, user_message: str, route: ChatRoute, chat_history: str) -> Dict[str, Any]:
    query = route.document_query if route.document_query else user_message
    doc_evidence = retrieve_document_evidence(project_id, query)
    db_evidence = retrieve_database_evidence(db, project_id, user_message)
    
    all_sources = doc_evidence["sources"] + db_evidence["sources"]
    unique_sources = []
    seen_ids = set()
    for s in all_sources:
        if s['id'] not in seen_ids:
            unique_sources.append(s)
            seen_ids.add(s['id'])

    prompt = f"""Bạn là AI Project Management Copilot.

LỊCH SỬ TRÒ CHUYỆN:
{chat_history if chat_history else 'Chưa có lịch sử'}

Bạn được cung cấp 2 nhóm evidence:

1. DATABASE_EVIDENCE (Dữ liệu hiện tại trong hệ thống như project, task, sprint):
{db_evidence['context']}

2. DOCUMENT_EVIDENCE (Nội dung được trích xuất từ tài liệu dự án):
{doc_evidence['context'] if doc_evidence['context'] else "TRỐNG - Không có thông tin tài liệu liên quan."}

Quy tắc:
- Chỉ trả lời từ evidence.
- Nếu phần nào không có evidence, nói rõ phần đó chưa có dữ liệu.
- Không trộn lẫn nguồn.
- Khi trả lời, phân tách rõ các mục:
  "Theo tài liệu:" (Chỉ dùng DOCUMENT_EVIDENCE, nếu trống thì báo không tìm thấy)
  "Theo dữ liệu hiện tại:" (Chỉ dùng DATABASE_EVIDENCE)
  "Kết luận:" 
- TUYỆT ĐỐI không dùng task evidence để trả lời câu hỏi về tài liệu nếu document evidence rỗng.

CÂU HỎI MỚI: {user_message}
"""

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        ai_answer = response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            ai_answer = "Hệ thống AI đang bị quá tải do hết hạn ngạch API (Rate Limit). Vui lòng đợi khoảng 1 phút rồi thử lại nhé!"
        else:
            ai_answer = f"Lỗi khi kết nối với AI: {error_msg}"
        
    save_chat_message(db, session_id, "assistant", ai_answer, {"mode": "hybrid", "route": route.model_dump(), "sources": unique_sources})
    return {"answer": ai_answer, "sources": unique_sources}

def handle_action_preview(db, project_id: str, session_id: str, user_message: str, route: ChatRoute, chat_history: str, user_role: str = None) -> Dict[str, Any]:
    from app.services.task_agent import handle_task_action
    
    # Ở phiên bản hiện tại, chúng ta mới hỗ trợ tạo Task. 
    # Nếu sau này có tạo Bug, tạo Sprint... thì có thể if/else thêm ở đây.
    
    return handle_task_action(db, project_id, session_id, user_message, chat_history, user_role)

def generate_chat_response(db, project_id: str, user_id: str, user_message: str, user_role: str = None) -> Dict[str, Any]:
    """
    Hàm tổng điều phối luồng xử lý tin nhắn:
    1. Lấy/tạo session
    2. Gọi Route Classifier
    3. Trả về kết quả dựa trên route
    """
    session_id = get_or_create_session(db, project_id, user_id)
    
    # 1. Exact Match Cache Check (Session Level)
    cache_key = f"{session_id}_{user_message.strip().lower()}"
    if cache_key in EXACT_MATCH_CACHE:
        # Clone response từ cache và lưu lại tin nhắn user
        cached_response = EXACT_MATCH_CACHE[cache_key]
        save_chat_message(db, session_id, "user", user_message)
        save_chat_message(db, session_id, "assistant", cached_response["answer"], {
            "mode": "cache_hit", 
            "sources": cached_response.get("sources", []), 
            "action_preview": cached_response.get("action_preview", None)
        })
        return cached_response
        
    # 2. Get Chat History (before saving new user message so we don't include it in history to LLM as past)
    chat_history = get_chat_history(db, session_id, limit=10)
    
    # 3. Save current user message
    save_chat_message(db, session_id, "user", user_message)
    
    # 4. Route with history
    route = route_message(user_message, project_id, user_id, chat_history)
    print(f"--- ROUTE PLAN ---\n{route.model_dump_json(indent=2)}\n------------------")
    
    # 5. Process
    if route.mode == "db_qa":
        result = answer_from_database(db, project_id, session_id, user_message, route, chat_history)
    elif route.mode == "document_rag":
        result = answer_from_documents(db, project_id, session_id, user_message, route, chat_history)
    elif route.mode == "hybrid":
        result = answer_hybrid(db, project_id, session_id, user_message, route, chat_history)
    elif route.mode == "action":
        result = handle_action_preview(db, project_id, session_id, user_message, route, chat_history, user_role)
    else:
        result = {"answer": "Bạn có thể nói rõ hơn bạn muốn hỏi về task hiện tại, tài liệu dự án, hay muốn tôi thực hiện thao tác nào không?", "sources": []}
        
    # Lưu vào Cache nếu không phải lỗi
    if "quá tải" not in result.get("answer", "").lower() and "không thể tạo tác vụ" not in result.get("answer", "").lower():
        EXACT_MATCH_CACHE[cache_key] = result
    
    # Để tránh phình to RAM, nếu cache > 1000 items thì clear
    if len(EXACT_MATCH_CACHE) > 1000:
        EXACT_MATCH_CACHE.clear()
        
    return result
