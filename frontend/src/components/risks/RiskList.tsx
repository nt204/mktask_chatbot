import { useState, useEffect } from 'react';
import { AlertTriangle, Clock } from 'lucide-react';
import './RiskList.css';

export default function RiskList({ projectId }: { projectId: string }) {
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/projects/${projectId}/risks`)
      .then(res => res.json())
      .then(data => {
        setRisks(data);
        setLoading(false);
      });
  }, [projectId]);

  if (loading) return <div>Loading risks...</div>;
  if (risks.length === 0) return <div className="card text-center text-secondary">No risks detected for this project.</div>;

  return (
    <div className="risk-list">
      {risks.map((risk: any) => (
        <div key={risk.id} className="card risk-card">
          <div className="risk-header">
            <div className="risk-title-group">
              <AlertTriangle className={`risk-icon-${risk.severity}`} size={20} />
              <h3>{risk.title}</h3>
            </div>
            <span className={`badge badge-risk-${risk.severity}`}>{risk.severity}</span>
          </div>
          
          <div className="risk-body">
            <p className="risk-desc">{risk.description}</p>
            {risk.task_title && (
              <div className="risk-task-ref">
                <strong>Related Task:</strong> {risk.task_title}
              </div>
            )}
            {risk.suggestion && (
              <div className="risk-suggestion">
                <strong>AI Suggestion:</strong> {risk.suggestion}
              </div>
            )}
          </div>
          
          <div className="risk-footer">
            <span className="risk-detected-by">Detected by {risk.detected_by.toUpperCase()}</span>
            <div className="risk-date">
              <Clock size={14} />
              <span>{new Date(risk.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
