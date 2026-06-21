import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Bot, User, CheckCircle, XCircle } from 'lucide-react';
import './ChatPanel.css';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  action_preview?: {
    tool: string;
    payload: any;
  };
  action_state?: 'pending' | 'success' | 'error' | 'cancelled';
}

export default function ChatPanel() {
  const { id: projectId } = useParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    const fetchHistory = async () => {
      if (!projectId) return;
      setIsLoading(true);
      try {
        const userEmail = localStorage.getItem('activeUserEmail') || '';
        const response = await fetch(`http://localhost:8000/api/chat/${projectId}/history`, {
          headers: { 'X-User-Email': userEmail }
        });
        if (response.ok) {
          const data = await response.json();
          setMessages(data);
        }
      } catch (error) {
        console.error("Failed to fetch chat history:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [projectId]);

  const handleSend = async () => {
    if (!input.trim() || !projectId || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const userEmail = localStorage.getItem('activeUserEmail') || '';
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Email': userEmail
        },
        body: JSON.stringify({
          project_id: projectId,
          message: userMsg
        })
      });

      const data = await response.json();
      
      if (response.ok) {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: data.answer, 
          sources: data.sources,
          action_preview: data.action_preview,
          action_state: data.action_preview ? 'pending' : undefined
        }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: `Lỗi: ${data.detail || 'Không thể kết nối AI'}` }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Lỗi kết nối máy chủ." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleActionConfirm = async (msgIdx: number, tool: string, payload: any) => {
    if (tool !== 'create_task_preview') return;
    
    try {
      const createPayload = {
        title: payload.title,
        description: payload.description || "",
        status: "todo",
        priority: payload.priority || "medium",
        assignee_hint: payload.assignee_hint || null,
        assignee_id: null 
      };

      const userEmail = localStorage.getItem('activeUserEmail') || '';
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/tasks`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Email': userEmail
        },
        body: JSON.stringify(createPayload)
      });
      
      if (response.ok) {
        setMessages(prev => prev.map((msg, i) => i === msgIdx ? { ...msg, action_state: 'success' } : msg));
      } else {
        setMessages(prev => prev.map((msg, i) => i === msgIdx ? { ...msg, action_state: 'error' } : msg));
      }
    } catch (e) {
      setMessages(prev => prev.map((msg, i) => i === msgIdx ? { ...msg, action_state: 'error' } : msg));
    }
  };

  const handleActionCancel = (msgIdx: number) => {
    setMessages(prev => prev.map((msg, i) => i === msgIdx ? { ...msg, action_state: 'cancelled' } : msg));
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <Bot size={20} className="chat-icon" />
        <div className="chat-title">
          <h3>AI Copilot</h3>
          <span className="chat-status" style={{color: 'var(--primary-color)'}}>Action Agent Enabled</span>
        </div>
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-placeholder">
            <Bot size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
            <p>Xin chào! Tôi là Copilot có thể đọc tài liệu và hỗ trợ tạo công việc.</p>
            <span style={{ fontSize: '12px', opacity: 0.5, marginTop: '8px', display: 'block' }}>
              Gợi ý: "Tạo cho tôi task Fix lỗi đăng nhập, priority high"
            </span>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-bubble-wrapper ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="message-avatar bot-avatar"><Bot size={14} /></div>
                )}
                <div className="message-content-group">
                  <div className={`message-bubble ${msg.role}`}>
                    {msg.content}
                  </div>
                  
                  {msg.action_preview && (
                    <div className="action-preview-card">
                      <div className="action-preview-header">
                        <CheckCircle size={14} /> Xác nhận {msg.action_preview.tool === 'create_task_preview' ? 'Tạo Task' : 'Hành động'}
                      </div>
                      
                      <div className="action-preview-field">
                        <span className="action-preview-label">Tiêu đề</span>
                        <span className="action-preview-value">{msg.action_preview.payload.title}</span>
                      </div>
                      
                      <div className="action-preview-field">
                        <span className="action-preview-label">Độ ưu tiên</span>
                        <span className="action-preview-value" style={{textTransform: 'capitalize'}}>{msg.action_preview.payload.priority}</span>
                      </div>
                      
                      {msg.action_preview.payload.assignee_hint && (
                        <div className="action-preview-field">
                          <span className="action-preview-label">Gợi ý người nhận</span>
                          <span className="action-preview-value">{msg.action_preview.payload.assignee_hint}</span>
                        </div>
                      )}
                      
                      {msg.action_state === 'pending' && (
                        <div className="action-preview-actions">
                          <button 
                            className="action-btn cancel" 
                            onClick={() => handleActionCancel(idx)}
                          >
                            Hủy bỏ
                          </button>
                          <button 
                            className="action-btn confirm" 
                            onClick={() => handleActionConfirm(idx, msg.action_preview!.tool, msg.action_preview!.payload)}
                          >
                            Xác nhận Tạo
                          </button>
                        </div>
                      )}
                      
                      {msg.action_state === 'success' && (
                        <div className="action-status success">
                          ✅ Đã tạo thành công! (Reload trang để xem Task mới)
                        </div>
                      )}
                      
                      {msg.action_state === 'error' && (
                        <div className="action-status error">
                          ❌ Tạo thất bại. Vui lòng thử lại.
                        </div>
                      )}
                      
                      {msg.action_state === 'cancelled' && (
                        <div className="action-status error" style={{background: 'transparent', color: 'var(--text-secondary)'}}>
                          Đã hủy hành động.
                        </div>
                      )}
                    </div>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="message-sources">
                      <span className="sources-title">Nguồn tham khảo:</span>
                      <ul>
                        {msg.sources.filter(s => s.type !== 'project_status').map((source, sIdx) => {
                          if (source.type === 'document') {
                            return (
                              <li key={sIdx} className="source-item document-source">
                                <span className="source-icon">📄</span> 
                                <span className="source-title">{source.title}</span>
                              </li>
                            );
                          }
                          if (source.type === 'task') {
                            return (
                              <li key={sIdx} className="source-item task-source">
                                <span className="source-icon">✅</span> 
                                <span className="source-title">Task: {source.title}</span>
                              </li>
                            );
                          }
                          return (
                            <li key={sIdx}>
                              <span className="source-tag">{source.type}</span> {source.title}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="message-avatar user-avatar"><User size={14} /></div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="message-bubble-wrapper assistant">
                <div className="message-avatar bot-avatar"><Bot size={14} /></div>
                <div className="message-bubble assistant loading-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      <div className="chat-input-area">
        <div className="chat-input-box">
          <input 
            type="text" 
            placeholder="Hỏi AI Copilot..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={isLoading || !projectId}
          />
          <button 
            className="chat-send-btn" 
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !projectId}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
