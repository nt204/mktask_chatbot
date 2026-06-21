from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

def get_risks_by_project(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT r.*, t.title as task_title
            FROM risk_events r
            LEFT JOIN tasks t ON r.task_id = t.id
            WHERE r.project_id = %s
            ORDER BY r.created_at DESC
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()

def get_top_risks_by_project(db, project_id: str, limit: int = 2) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT risk_type as type, severity, title
            FROM risk_events
            WHERE project_id = %s AND status = 'open'
            ORDER BY 
              CASE severity 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
                ELSE 4 
              END, 
              created_at DESC
            LIMIT %s
        """, (project_id, limit))
        return cur.fetchall()
    finally:
        cur.close()

def get_risk_counts_by_severity(db, project_id: str) -> Dict[str, int]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT severity, COUNT(*) as count
            FROM risk_events
            WHERE project_id = %s AND status = 'open'
            GROUP BY severity
        """, (project_id,))
        rows = cur.fetchall()
        return {row['severity']: row['count'] for row in rows}
    finally:
        cur.close()

def get_open_risks(db, project_id: str) -> List[Dict[str, Any]]:
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, title, risk_type as type, severity, status
            FROM risk_events
            WHERE project_id = %s AND status = 'open'
            ORDER BY created_at DESC
        """, (project_id,))
        return cur.fetchall()
    finally:
        cur.close()
