import { CheckSquare, Users, Activity, Clock, AlertTriangle } from 'lucide-react';
import './ProjectOverview.css';

export default function ProjectOverview({ project }: { project: any }) {
  return (
    <div className="overview-container">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8' }}>
            <CheckSquare size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Total Tasks</span>
            <span className="stat-value">{project.total_tasks}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#34d399' }}>
            <Activity size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Tasks Done</span>
            <span className="stat-value">{project.tasks_done}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24' }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">In Progress</span>
            <span className="stat-value">{project.tasks_in_progress}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#f87171' }}>
            <AlertTriangle size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Blocked/Risks</span>
            <span className="stat-value">{project.tasks_blocked} / {project.open_risks}</span>
          </div>
        </div>
      </div>

      <div className="overview-content">
        <div className="card member-list-card">
          <h3>Team Members</h3>
          <div className="member-list">
            {project.members && project.members.map((m: any) => (
              <div key={m.id} className="member-item">
                <div className="member-avatar">{m.full_name.charAt(0)}</div>
                <div className="member-info">
                  <div className="member-name">{m.full_name}</div>
                  <div className="member-role">{m.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card recent-activity-card">
          <h3>Project Details</h3>
          <div className="detail-row">
            <span className="detail-label">Status</span>
            <span className={`badge badge-${project.status}`}>{project.status}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Start Date</span>
            <span>{new Date(project.start_date).toLocaleDateString()}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">End Date</span>
            <span>{new Date(project.end_date).toLocaleDateString()}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Total Sprints</span>
            <span>{project.total_sprints}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
