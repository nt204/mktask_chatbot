import os
import fitz  # PyMuPDF
from uuid import UUID
from typing import List, Dict, Any
from psycopg2.extras import RealDictCursor
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from google import genai
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Khởi tạo Qdrant Client (chạy local qua Docker)
qdrant = QdrantClient(host="localhost", port=6333)

COLLECTION_NAME = "project_documents"

# Khởi tạo Collection nếu chưa có
try:
    qdrant.get_collection(COLLECTION_NAME)
except Exception:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
    )

api_key = os.getenv("GEMINI_API_KEY")
genai_client = genai.Client(api_key=api_key) if api_key else None

def get_project_documents(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, filename, file_type, index_status, created_at 
            FROM documents
            WHERE project_id = %s
            ORDER BY created_at DESC
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()

def save_document_record(db, project_id: str, user_id: str, filename: str, storage_url: str) -> str:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO documents (project_id, uploaded_by, filename, storage_url, index_status)
            VALUES (%s, %s, %s, %s, 'processing')
            RETURNING id
        """, (project_id, user_id, filename, storage_url))
        doc_id = cur.fetchone()['id']
        db.commit()
        return doc_id
    finally:
        cur.close()

def update_document_status(db, doc_id: str, status: str):
    cur = db.cursor()
    try:
        cur.execute("UPDATE documents SET index_status = %s WHERE id = %s", (status, doc_id))
        db.commit()
    finally:
        cur.close()

def process_document(db, doc_id: str, filepath: str, project_id: str, filename: str):
    """
    ========================================================================
    HÀM CỐT LÕI CỦA RAG: XỬ LÝ TÀI LIỆU VÀ ĐƯA VÀO VECTOR DB
    Dành cho người mới học: Máy tính không tự nhiên hiểu được 1 cuốn sách.
    Chúng ta phải làm 3 bước:
    1. Đọc sách (Extract Text).
    2. Xé nhỏ sách ra từng trang/đoạn (Chunking) để máy tính dễ nuốt.
    3. Biến mỗi đoạn chữ thành một chuỗi số (Embedding) và cất vào Qdrant.
    ========================================================================
    """
    try:
        # BƯỚC 1: TRÍCH XUẤT CHỮ (EXTRACT TEXT)
        # Nếu là file PDF, dùng thư viện PyMuPDF (fitz) để quét từng trang
        # và rút hết chữ text ra thành một đoạn văn bản khổng lồ.
        text = ""
        if filepath.endswith(".pdf"):
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text() + "\n"
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

        # BƯỚC 2: CHIA NHỎ VĂN BẢN (CHUNKING bằng LANGCHAIN)
        # Tại sao phải băm nhỏ? Vì AI (LLM) có giới hạn đọc (Context Window).
        # Nếu ném cả cuốn sách 1000 trang vào, nó sẽ bị tràn bộ nhớ hoặc nhớ nhầm.
        # Ở đây ta dùng LangChain cắt mỗi khúc 500 ký tự.
        # "chunk_overlap=100" nghĩa là đoạn sau sẽ lặp lại 100 ký tự của đoạn trước 
        # để không bị cắt đứt ý giữa chừng (ví dụ cắt trúng giữa 1 câu).
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_text(text)

        if not chunks:
            update_document_status(db, doc_id, 'failed')
            return

        if not genai_client:
            update_document_status(db, doc_id, 'failed')
            print("No Gemini API key")
            return

        # BƯỚC 3: TẠO EMBEDDING (Mã hóa từ ngữ thành những con số)
        # Máy tính chỉ hiểu toán học. Ta nhờ Google Gemini chuyển từng "đoạn chữ"
        # thành một "Vector" (danh sách gồm 768 con số).
        # Những đoạn văn có ý nghĩa giống nhau sẽ có các con số gần giống nhau.
        # Lưu ý: Ta chia thành từng batch nhỏ (VD 50 chunks/lần) để Google không báo lỗi 400 Bad Request
        embeddings = []
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            response = genai_client.models.embed_content(
                model='gemini-embedding-2',
                contents=batch
            )
            embeddings.extend(response.embeddings)

        # BƯỚC 4: LƯU VÀO VECTOR DB (QDRANT)
        # Vector Database sinh ra để lưu trữ và tính toán khoảng cách giữa các Vector cực nhanh.
        # Ở đây ta lưu 3 thứ cho mỗi Chunk:
        # 1. ID duy nhất.
        # 2. Vector (dãy số vừa được Google tạo ra).
        # 3. Payload (dữ liệu đi kèm, ví dụ như nội dung chữ gốc là gì, của dự án nào).
        points = []
        import uuid
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb.values,
                    payload={
                        "project_id": str(project_id),
                        "document_id": str(doc_id),
                        "filename": filename,
                        "chunk_index": i,
                        "text": chunk
                    }
                )
            )
        
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

        # 5. Cập nhật trạng thái
        update_document_status(db, doc_id, 'indexed')

    except Exception as e:
        print(f"Error processing doc: {e}")
        update_document_status(db, doc_id, 'failed')

def search_documents(project_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    ========================================================================
    HÀM TÌM KIẾM THEO NGỮ NGHĨA (SEMANTIC SEARCH)
    Thay vì tìm theo từ khóa (LIKE %...%), ta tìm bằng ý nghĩa.
    Cách làm: 
    1. Biến câu hỏi của user thành Vector.
    2. Yêu cầu Qdrant tìm 5 Vector (5 đoạn văn) trong kho có khoảng cách toán học 
       GẦN NHẤT với Vector câu hỏi.
    ========================================================================
    """
    if not genai_client:
        return []

    try:
        # Tạo embedding cho câu hỏi
        response = genai_client.models.embed_content(
            model='gemini-embedding-2',
            contents=query
        )
        query_vector = response.embeddings[0].values

        # Tìm kiếm trên Qdrant
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        search_result = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="project_id",
                        match=MatchValue(value=str(project_id))
                    )
                ]
            ),
            limit=top_k
        ).points

        # Trả về payload (chứa text, filename)
        return [hit.payload for hit in search_result]

    except Exception as e:
        print(f"Error searching docs: {e}")
        return []
