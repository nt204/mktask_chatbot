from fastapi import Depends, HTTPException, status, Request
from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from app.db.database import get_db

def get_current_user(request: Request, db=Depends(get_db)) -> Dict[str, Any]:
    """
    Mock current user reading from X-User-Email header for testing RBAC.
    """
    email = request.headers.get("X-User-Email")
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        if email:
            cur.execute("SELECT * FROM users WHERE email = %s LIMIT 1", (email,))
            user = cur.fetchone()
            if user:
                return user
                
        # Fallback to PM if no header
        cur.execute("SELECT * FROM users WHERE global_role = 'PM' LIMIT 1")
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="No mock user found")
        return user
    finally:
        cur.close()

def check_project_access(project_id: str, current_user: Dict[str, Any] = Depends(get_current_user), db=Depends(get_db)):
    """
    Check if the current user has access to the given project.
    """
    # Directors have access to all projects
    if current_user.get('global_role') in ['ADMIN', 'DIRECTOR']:
        return current_user

    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT role FROM project_members 
            WHERE project_id = %s AND user_id = %s
        """, (project_id, current_user['id']))
        
        member = cur.fetchone()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have access to this project"
            )
        
        # Attach project role to the current user object for downstream use
        current_user['project_role'] = member['role']
        return current_user
    finally:
        cur.close()

def require_project_role(allowed_roles: List[str]):
    def role_checker(current_user: Dict[str, Any] = Depends(check_project_access)):
        if current_user.get('global_role') in ['ADMIN', 'DIRECTOR']:
            return current_user
            
        role = current_user.get('project_role')
        if not role or role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"You need one of these roles: {allowed_roles} to perform this action. Your role: {role}"
            )
        return current_user
    return role_checker
