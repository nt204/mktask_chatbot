import os
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from app.db.database import get_db
from app.core.security import get_current_user
from app.services import document_service
import shutil

router = APIRouter()

@router.post("/projects/{project_id}/documents/upload")
async def upload_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        # Save file to local uploads directory
        filename = file.filename
        filepath = os.path.join(document_service.UPLOAD_DIR, f"{project_id}_{filename}")
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create record in database
        doc_id = document_service.save_document_record(
            db, project_id, current_user['id'], filename, filepath
        )

        # Trigger background processing (chunking, embedding, Qdrant)
        background_tasks.add_task(
            document_service.process_document,
            db, doc_id, filepath, project_id, filename
        )

        return {"message": "File uploaded successfully. Processing started.", "document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/documents")
def list_documents(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        docs = document_service.get_project_documents(db, project_id)
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
