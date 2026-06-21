from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.db.database import get_db
from app.core.security import check_project_access
from app.services import status_service

# We mount this under /projects/{project_id}/status but define the router carefully
# Or we can just use the projects router. Since the requirement says "status_service.py",
# having a separate router for status is a bit tricky with path prefixes. 
# We'll just define it here and mount it in main.py without a prefix, or prefix it with /projects

router = APIRouter(prefix="/projects", tags=["status"])

@router.get("/{project_id}/status", response_model=Dict[str, Any])
def get_project_status(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    status_data = status_service.get_project_status(db, project_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Project not found")
    return status_data
