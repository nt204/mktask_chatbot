import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader, X } from 'lucide-react';
import './DocumentsPanel.css';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  index_status: string;
  created_at: string;
}

export default function DocumentsPanel({ projectId }: { projectId: string }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = () => {
    fetch(`http://localhost:8000/api/projects/${projectId}/documents`)
      .then(res => res.json())
      .then(data => {
        setDocuments(data.documents || []);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDocuments();
    // Polling to update index_status
    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, [projectId]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`http://localhost:8000/api/projects/${projectId}/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        fetchDocuments();
      } else {
        alert("Upload failed");
      }
    } catch (error) {
      alert("Error uploading file");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'indexed':
        return <span className="badge badge-success"><CheckCircle size={12}/> Indexed</span>;
      case 'processing':
      case 'pending':
        return <span className="badge badge-warning"><Loader size={12} className="spin" /> Processing</span>;
      case 'failed':
        return <span className="badge badge-error"><AlertCircle size={12}/> Failed</span>;
      default:
        return <span className="badge badge-secondary">{status}</span>;
    }
  };

  return (
    <div className="documents-panel card p-6">
      <div className="panel-header">
        <h2>Project Documents</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleUploadClick}
          disabled={uploading}
        >
          {uploading ? <Loader size={16} className="spin" /> : <Upload size={16} />} 
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".pdf,.txt"
          onChange={handleFileChange}
        />
      </div>

      <p className="text-secondary mt-2 mb-4">
        Tải lên tài liệu dự án (PDF, TXT) để AI có thể đọc và hỗ trợ trả lời câu hỏi của bạn.
      </p>

      {loading ? (
        <div className="p-4 text-center">Loading...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} />
          <p>Chưa có tài liệu nào.</p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Tên File</th>
              <th>Ngày Tải Lên</th>
              <th>Trạng Thái (AI)</th>
              <th>Thao Tác</th>
            </tr>
          </thead>
          <tbody>
            {documents.map(doc => (
              <tr key={doc.id}>
                <td>
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-secondary" />
                    <strong>{doc.filename}</strong>
                  </div>
                </td>
                <td>{new Date(doc.created_at).toLocaleString('vi-VN')}</td>
                <td>{getStatusBadge(doc.index_status || 'pending')}</td>
                <td>
                  <button className="btn btn-icon btn-ghost"><X size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
