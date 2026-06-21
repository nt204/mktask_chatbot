import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Users, CheckSquare, Clock } from 'lucide-react';
import './Projects.css';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/projects')
      .then(res => res.json())
      .then(data => {
        setProjects(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching projects:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '24px' }}>Projects</h1>
        <div className="projects-grid">
          {[1, 2, 3].map(i => <div key={i} className="card skeleton" style={{ height: '200px' }}></div>)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center" style={{ marginBottom: '24px' }}>
        <h1>Projects</h1>
        <button className="btn btn-primary">New Project</button>
      </div>

      <div className="projects-grid">
        {projects.map((project: any) => (
          <Link to={`/projects/${project.id}`} key={project.id} className="card project-card">
            <div className="project-header">
              <h3>{project.name}</h3>
              <span className={`status-badge ${project.status}`}>{project.status}</span>
            </div>
            
            <p className="project-desc">{project.description}</p>
            
            <div className="project-stats">
              <div className="stat-item">
                <CheckSquare size={16} />
                <span>{project.total_tasks} Tasks</span>
              </div>
              <div className="stat-item">
                <Users size={16} />
                <span>{project.total_members} Members</span>
              </div>
            </div>
            
            <div className="project-footer">
              <div className="date">
                <Clock size={14} />
                <span>{new Date(project.start_date).toLocaleDateString()}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
