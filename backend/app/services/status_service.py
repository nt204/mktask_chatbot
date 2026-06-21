from typing import Dict, Any
from app.services import project_service, task_service, risk_service

def get_project_status(db, project_id: str) -> Dict[str, Any]:
    project = project_service.get_project_by_id(db, project_id)
    if not project:
        return None
        
    # Task stats
    task_counts = task_service.get_task_counts_by_status(db, project_id)
    overdue_count = task_service.get_overdue_tasks_count(db, project_id)
    total_tasks = sum(task_counts.values())
    
    # Sprints
    sprints = project_service.get_project_sprints(db, project_id)
    current_sprint_name = None
    sprint_total_tasks = 0
    sprint_done_tasks = 0
    sprint_progress = 0
    
    active_sprint = next((s for s in sprints if s['status'] == 'active'), None)
    if active_sprint:
        current_sprint_name = active_sprint['name']
        sprint_total_tasks = active_sprint['total_tasks']
        sprint_done_tasks = active_sprint['completed_tasks']
        sprint_progress = active_sprint['progress']
    elif sprints:
        # If no active, grab latest
        last_sprint = sprints[-1]
        current_sprint_name = last_sprint['name']
        sprint_total_tasks = last_sprint['total_tasks']
        sprint_done_tasks = last_sprint['completed_tasks']
        sprint_progress = last_sprint['progress']
        
    # Risks
    risk_counts = risk_service.get_risk_counts_by_severity(db, project_id)
    open_risks = sum(risk_counts.values())
    top_risks = risk_service.get_top_risks_by_project(db, project_id, limit=2)
    
    return {
        "project": {
            "id": project['id'],
            "name": project['name'],
            "status": project['status'],
            "start_date": project['start_date'].isoformat() if project['start_date'] else None,
            "end_date": project['end_date'].isoformat() if project['end_date'] else None
        },
        "task_summary": {
            "total": total_tasks,
            "todo": task_counts.get('todo', 0),
            "in_progress": task_counts.get('in_progress', 0),
            "review": task_counts.get('review', 0),
            "done": task_counts.get('done', 0),
            "blocked": task_counts.get('blocked', 0),
            "overdue": overdue_count
        },
        "sprint_summary": {
            "current_sprint": current_sprint_name,
            "total_tasks": sprint_total_tasks,
            "done_tasks": sprint_done_tasks,
            "progress_percent": sprint_progress
        },
        "risk_summary": {
            "open_risks": open_risks,
            "high": risk_counts.get('high', 0),
            "medium": risk_counts.get('medium', 0),
            "low": risk_counts.get('low', 0)
        },
        "top_risks": top_risks
    }
