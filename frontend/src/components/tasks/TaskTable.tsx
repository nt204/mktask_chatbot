import { useState, useEffect } from 'react';
import './TaskTable.css';

export default function TaskTable({ projectId }: { projectId: string }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/projects/${projectId}/tasks`)
      .then(res => res.json())
      .then(data => {
        setTasks(data);
        setLoading(false);
      });
  }, [projectId]);

  if (loading) return <div>Loading tasks...</div>;

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <table className="task-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Assignee</th>
            <th>Due Date</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task: any) => (
            <tr key={task.id} className="task-row">
              <td className="task-title-cell">
                <span className="task-title">{task.title}</span>
                {task.sprint_name && <span className="sprint-tag">{task.sprint_name}</span>}
              </td>
              <td>
                <span className={`badge badge-${task.status}`}>
                  {task.status.replace('_', ' ')}
                </span>
              </td>
              <td>
                <span className={`badge-priority-${task.priority}`} style={{ textTransform: 'capitalize', fontSize: '13px', fontWeight: 500 }}>
                  {task.priority}
                </span>
              </td>
              <td>
                {task.assignee_name ? (
                  <div className="task-assignee">
                    <div className="assignee-avatar-small">{task.assignee_name.charAt(0)}</div>
                    <span>{task.assignee_name}</span>
                  </div>
                ) : (
                  <span style={{ color: 'var(--text-secondary)' }}>Unassigned</span>
                )}
              </td>
              <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                {task.due_date ? new Date(task.due_date).toLocaleDateString() : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
