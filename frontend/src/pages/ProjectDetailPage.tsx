import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, MessageSquare, AlertTriangle, CheckSquare, Activity, FileText, ArrowRight } from 'lucide-react';
import ProjectOverview from '../components/projects/ProjectOverview';
import TaskTable from '../components/tasks/TaskTable';
import SprintList from '../components/projects/SprintList';
import RiskList from '../components/risks/RiskList';
import ChatPanel from '../components/chat/ChatPanel';
import DocumentsPanel from '../components/documents/DocumentsPanel';
import './ProjectDetail.css';

export default function ProjectDetailPage() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/projects/${id}`)
      .then(res => res.json())
      .then(data => {
        setProject(data);
        setLoading(false);
      });
  }, [id]);

  if (loading || !project) {
    return <div className="p-8">Loading project...</div>;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'overview': return <ProjectOverview project={project} />;
      case 'tasks': return <TaskTable projectId={project.id} />;
      case 'sprints': return <SprintList projectId={project.id} />;
      case 'risks': return <RiskList projectId={project.id} />;
      case 'documents': return <DocumentsPanel projectId={project.id} />;
      case 'chat': return <ChatPanel />;
      default: return <div className="card" style={{ padding: '40px', textAlign: 'center' }}>Coming soon...</div>;
    }
  };

  return (
    <div className="project-detail-layout">
      <div className="project-main">
        <div className="breadcrumb">
          <Link to="/projects" className="back-link">
            <ChevronLeft size={16} /> Projects
          </Link>
          <span className="separator">/</span>
          <span className="current">{project.name}</span>
        </div>

        <div className="project-header-section">
          <div>
            <h1>{project.name}</h1>
            <p className="project-description">{project.description}</p>
          </div>
          <div className="actions">
            <button className="btn btn-primary">Edit Project</button>
          </div>
        </div>

        <div className="tabs">
          <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
            <Activity size={16} /> Overview
          </button>
          <button className={`tab ${activeTab === 'tasks' ? 'active' : ''}`} onClick={() => setActiveTab('tasks')}>
            <CheckSquare size={16} /> Tasks
          </button>
          <button className={`tab ${activeTab === 'sprints' ? 'active' : ''}`} onClick={() => setActiveTab('sprints')}>
            <ArrowRight size={16} /> Sprints
          </button>
          <button className={`tab ${activeTab === 'risks' ? 'active' : ''}`} onClick={() => setActiveTab('risks')}>
            <AlertTriangle size={16} /> Risks
            {project.open_risks > 0 && <span className="tab-badge">{project.open_risks}</span>}
          </button>
          <button className={`tab ${activeTab === 'documents' ? 'active' : ''}`} onClick={() => setActiveTab('documents')}>
            <FileText size={16} /> Documents
          </button>
        </div>

        <div className="tab-content page-enter">
          {renderContent()}
        </div>
      </div>
      
      {/* Right Sidebar for AI Chat */}
      <div className="project-sidebar">
        <ChatPanel />
      </div>
    </div>
  );
}
