from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

def get_tasks_by_project(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.*, 
                   u.full_name as assignee_name, u.avatar_url as assignee_avatar,
                   s.name as sprint_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            LEFT JOIN sprints s ON t.sprint_id = s.id
            WHERE t.project_id = %s
            ORDER BY t.created_at DESC
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()

def create_task(db, project_id: str, title: str, description: str = "", status: str = "todo", priority: str = "medium", assignee_id: str = None, reporter_id: str = None) -> Dict[str, Any]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO tasks (project_id, title, description, status, priority, assignee_id, reporter_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (project_id, title, description, status, priority, assignee_id, reporter_id))
        new_task = cur.fetchone()
        db.commit()
        return new_task
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cur.close()

def get_task_by_id(db, task_id: str) -> Dict[str, Any]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.*, 
                   u.full_name as assignee_name, u.avatar_url as assignee_avatar,
                   s.name as sprint_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            LEFT JOIN sprints s ON t.sprint_id = s.id
            WHERE t.id = %s
        """, (task_id,))
        return cur.fetchone()
    finally:
        cur.close()

def get_task_counts_by_status(db, project_id: str) -> Dict[str, int]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM tasks
            WHERE project_id = %s
            GROUP BY status
        """, (project_id,))
        rows = cur.fetchall()
        return {row['status']: row['count'] for row in rows}
    finally:
        cur.close()

def get_overdue_tasks_count(db, project_id: str) -> int:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT COUNT(*) as count
            FROM tasks
            WHERE project_id = %s
              AND due_date < CURRENT_DATE
              AND status != 'done'
        """, (project_id,))
        return cur.fetchone()['count']
    finally:
        cur.close()

def get_blocked_tasks(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT * FROM tasks
            WHERE project_id = %s AND status = 'blocked'
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()
