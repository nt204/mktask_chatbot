from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.db.database import get_db
from app.core.security import get_current_user
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}", response_model=Dict[str, Any])
def get_task(task_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    # Basic check - in a real app, you would check if current_user has access to the task's project
    task = task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
