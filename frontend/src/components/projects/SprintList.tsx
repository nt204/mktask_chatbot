import { useState, useEffect } from 'react';
import './SprintList.css';

export default function SprintList({ projectId }: { projectId: string }) {
  const [sprints, setSprints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/projects/${projectId}/sprints`)
      .then(res => res.json())
      .then(data => {
        setSprints(data);
        setLoading(false);
      });
  }, [projectId]);

  if (loading) return <div>Loading sprints...</div>;

  return (
    <div className="sprint-list">
      {sprints.map((sprint: any) => (
        <div key={sprint.id} className="card sprint-card">
          <div className="sprint-header">
            <h3>{sprint.name}</h3>
            <span className={`badge badge-${sprint.status === 'active' ? 'in_progress' : sprint.status}`}>
              {sprint.status}
            </span>
          </div>
          
          <p className="sprint-goal">{sprint.goal}</p>
          
          <div className="sprint-dates">
            <span>{new Date(sprint.start_date).toLocaleDateString()}</span>
            <span>-</span>
            <span>{new Date(sprint.end_date).toLocaleDateString()}</span>
          </div>
          
          <div className="sprint-progress-section">
            <div className="progress-labels">
              <span>Progress</span>
              <span>{sprint.progress}% ({sprint.completed_tasks}/{sprint.total_tasks} tasks)</span>
            </div>
            <div className="progress-bar-bg">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${sprint.progress}%`, background: sprint.progress === 100 ? 'var(--success-color)' : 'var(--primary-color)' }}
              ></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
