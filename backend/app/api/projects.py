from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.db.database import get_db
from app.core.security import get_current_user, check_project_access, require_project_role
from app.services import project_service, task_service, risk_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=List[Dict[str, Any]])
def get_projects(db=Depends(get_db), current_user=Depends(get_current_user)):
    return project_service.get_all_projects(db, current_user['id'], current_user['global_role'])

@router.get("/{project_id}", response_model=Dict[str, Any])
def get_project(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    project = project_service.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project['members'] = project_service.get_project_members(db, project_id)
    
    # basic task stats for backwards compatibility with Phase 1 frontend
    task_counts = task_service.get_task_counts_by_status(db, project_id)
    project['total_tasks'] = sum(task_counts.values())
    project['tasks_todo'] = task_counts.get('todo', 0)
    project['tasks_in_progress'] = task_counts.get('in_progress', 0)
    project['tasks_done'] = task_counts.get('done', 0)
    project['tasks_blocked'] = task_counts.get('blocked', 0)
    
    sprints = project_service.get_project_sprints(db, project_id)
    project['total_sprints'] = len(sprints)
    
    risk_counts = risk_service.get_risk_counts_by_severity(db, project_id)
    project['open_risks'] = sum(risk_counts.values())
    project['high_risks'] = risk_counts.get('high', 0)
    
    return project

@router.get("/{project_id}/members", response_model=List[Dict[str, Any]])
def get_project_members(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    return project_service.get_project_members(db, project_id)

@router.get("/{project_id}/sprints", response_model=List[Dict[str, Any]])
def get_project_sprints(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    return project_service.get_project_sprints(db, project_id)

@router.get("/{project_id}/tasks", response_model=List[Dict[str, Any]])
def get_project_tasks(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    return task_service.get_tasks_by_project(db, project_id)

from pydantic import BaseModel
from typing import Optional

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    assignee_id: Optional[str] = None
    assignee_hint: Optional[str] = None

@router.post("/{project_id}/tasks", response_model=Dict[str, Any])
def create_project_task(project_id: str, payload: TaskCreate, db=Depends(get_db), current_user=Depends(require_project_role(['PM', 'TEAM_LEAD', 'ADMIN', 'DIRECTOR']))):
    try:
        actual_assignee_id = payload.assignee_id
        
        # Tự động Auto-match tên người dùng (assignee_hint) thành ID
        if not actual_assignee_id and payload.assignee_hint:
            members = project_service.get_project_members(db, project_id)
            hint_lower = payload.assignee_hint.lower()
            for m in members:
                if hint_lower in m['full_name'].lower() or hint_lower in m['email'].lower():
                    actual_assignee_id = m['id']
                    break
                    
        new_task = task_service.create_task(
            db=db,
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            assignee_id=actual_assignee_id,
            reporter_id=current_user['id']
        )
        return new_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/risks", response_model=List[Dict[str, Any]])
def get_project_risks(project_id: str, db=Depends(get_db), current_user=Depends(check_project_access)):
    return risk_service.get_risks_by_project(db, project_id)
