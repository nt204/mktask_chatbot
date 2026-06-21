from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

def get_all_projects(db, user_id: str = None, global_role: str = None) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        if global_role in ['ADMIN', 'DIRECTOR']:
            cur.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as total_tasks,
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.id) as total_members
                FROM projects p
                ORDER BY p.created_at DESC
            """)
        else:
            cur.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as total_tasks,
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.id) as total_members
                FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE pm.user_id = %s
                ORDER BY p.created_at DESC
            """, (user_id,))
        return cur.fetchall()
    finally:
        cur.close()

def get_project_by_id(db, project_id: str) -> Dict[str, Any]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        return cur.fetchone()
    finally:
        cur.close()

def get_project_members(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT u.id, u.full_name, u.avatar_url, u.email, pm.role 
            FROM project_members pm 
            JOIN users u ON pm.user_id = u.id 
            WHERE pm.project_id = %s
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()

def get_project_sprints(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT s.*,
                   (SELECT COUNT(*) FROM tasks t WHERE t.sprint_id = s.id) as total_tasks,
                   (SELECT COUNT(*) FROM tasks t WHERE t.sprint_id = s.id AND t.status = 'done') as completed_tasks
            FROM sprints s
            WHERE s.project_id = %s
            ORDER BY s.start_date ASC
        """, (project_id,))
        sprints = cur.fetchall()
        
        for sprint in sprints:
            if sprint['total_tasks'] > 0:
                sprint['progress'] = round((sprint['completed_tasks'] / sprint['total_tasks']) * 100)
            else:
                sprint['progress'] = 0
                
        return sprints
    finally:
        cur.close()
