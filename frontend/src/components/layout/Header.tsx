import { Search, Bell } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function Header() {
  const [users, setUsers] = useState<any[]>([]);
  const [activeUserEmail, setActiveUserEmail] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/api/users')
      .then(res => res.json())
      .then(data => {
        setUsers(data);
        const storedEmail = localStorage.getItem('activeUserEmail');
        if (storedEmail) {
            setActiveUserEmail(storedEmail);
        } else if (data.length > 0) {
            // Default to PM
            const pm = data.find((u: any) => u.global_role === 'PM') || data[0];
            setActiveUserEmail(pm.email);
            localStorage.setItem('activeUserEmail', pm.email);
        }
      });
  }, []);

  const handleUserChange = (e: any) => {
    const email = e.target.value;
    setActiveUserEmail(email);
    localStorage.setItem('activeUserEmail', email);
    window.location.reload();
  };

  return (
    <header className="header">
      <div className="header-search">
        <Search size={18} color="var(--text-secondary)" />
        <input type="text" placeholder="Search projects, tasks..." />
      </div>
      
      <div className="header-actions">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-secondary)', padding: '4px 12px', borderRadius: '20px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Login as:</span>
          <select 
            value={activeUserEmail} 
            onChange={handleUserChange}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none', fontSize: '14px', cursor: 'pointer', maxWidth: '200px' }}
          >
            {users.map(u => (
              <option key={u.id} value={u.email}>{u.full_name} ({u.global_role})</option>
            ))}
          </select>
        </div>
        <button className="action-btn">
          <Bell size={20} />
        </button>
      </div>
    </header>
  );
}
