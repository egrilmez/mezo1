// pages/admin.tsx - Admin Panel
import React, { useState, useEffect } from 'react';

interface Destination {
  id?: number;
  name: string;
  description: string;
  category: string;
  location: string;
  rating: number;
  image_url: string;
  tags: string[];
}

interface ChatHistory {
  message: string;
  response: string;
  timestamp: string;
}

export default function AdminPanel() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [newDestination, setNewDestination] = useState<Destination>({
    name: '',
    description: '',
    category: '',
    location: '',
    rating: 0,
    image_url: '',
    tags: []
  });

  useEffect(() => {
    fetchDestinations();
    fetchChatHistory();
  }, []);

  const fetchDestinations = async () => {
    try {
      const response = await fetch('http://localhost:8000/destinations');
      const data = await response.json();
      setDestinations(data);
    } catch (error) {
      console.error('Error fetching destinations:', error);
    }
  };

  const fetchChatHistory = async () => {
    // Fetch for all users - in production, this would be paginated
    try {
      const response = await fetch('http://localhost:8000/chat/history/admin?limit=50');
      const data = await response.json();
      setChatHistory(data.history || []);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  const stats = {
    totalDestinations: destinations.length,
    totalChats: chatHistory.length,
    avgRating: destinations.reduce((acc, d) => acc + d.rating, 0) / destinations.length || 0,
    topCategory: destinations.reduce((acc, d) => {
      acc[d.category] = (acc[d.category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  };

  return (
    <div className="admin-container">
      <style jsx>{`
        .admin-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          min-height: 100vh;
          background: #f5f5f5;
        }

        .admin-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px 40px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .admin-header h1 {
          margin: 0;
          font-size: 2rem;
        }

        .admin-nav {
          background: white;
          padding: 0 40px;
          box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        .nav-tabs {
          display: flex;
          gap: 30px;
          margin: 0;
          padding: 0;
          list-style: none;
        }

        .nav-tab {
          padding: 15px 0;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .nav-tab:hover {
          color: #667eea;
        }

        .nav-tab.active {
          color: #667eea;
          border-bottom-color: #667eea;
        }

        .admin-content {
          padding: 40px;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 40px;
        }

        .stat-card {
          background: white;
          padding: 20px;
          border-radius: 10px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .stat-label {
          color: #666;
          font-size: 14px;
          margin-bottom: 5px;
        }

        .stat-value {
          font-size: 2rem;
          font-weight: bold;
          color: #333;
        }

        .table-container {
          background: white;
          border-radius: 10px;
          padding: 20px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        table {
          width: 100%;
          border-collapse: collapse;
        }

        th {
          background: #f8f8f8;
          padding: 12px;
          text-align: left;
          font-weight: 600;
          color: #666;
          border-bottom: 2px solid #e0e0e0;
        }

        td {
          padding: 12px;
          border-bottom: 1px solid #f0f0f0;
        }

        tr:hover {
          background: #f9f9f9;
        }

        .form-container {
          background: white;
          border-radius: 10px;
          padding: 30px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
          max-width: 600px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-label {
          display: block;
          margin-bottom: 5px;
          font-weight: 500;
          color: #333;
        }

        .form-input {
          width: 100%;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 5px;
          font-size: 14px;
        }

        .form-input:focus {
          outline: none;
          border-color: #667eea;
        }

        .btn {
          padding: 10px 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 5px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn:hover {
          opacity: 0.9;
        }

        .tag-input {
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
          padding: 5px;
          border: 1px solid #ddd;
          border-radius: 5px;
          min-height: 40px;
        }

        .tag {
          background: #667eea;
          color: white;
          padding: 5px 10px;
          border-radius: 15px;
          font-size: 12px;
        }

        .chat-message {
          background: #f9f9f9;
          padding: 10px;
          border-radius: 5px;
          margin-bottom: 10px;
        }

        .message-user {
          font-weight: bold;
          color: #667eea;
        }

        .message-bot {
          color: #666;
          margin-top: 5px;
        }

        .message-time {
          font-size: 12px;
          color: #999;
        }
      `}</style>

      <div className="admin-header">
        <h1>🏛️ Mezopotamya.Travel Admin Panel</h1>
      </div>

      <nav className="admin-nav">
        <ul className="nav-tabs">
          <li 
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </li>
          <li 
            className={`nav-tab ${activeTab === 'destinations' ? 'active' : ''}`}
            onClick={() => setActiveTab('destinations')}
          >
            📍 Destinasyonlar
          </li>
          <li 
            className={`nav-tab ${activeTab === 'add-destination' ? 'active' : ''}`}
            onClick={() => setActiveTab('add-destination')}
          >
            ➕ Yeni Ekle
          </li>
          <li 
            className={`nav-tab ${activeTab === 'chats' ? 'active' : ''}`}
            onClick={() => setActiveTab('chats')}
          >
            💬 Sohbet Geçmişi
          </li>
        </ul>
      </nav>

      <div className="admin-content">
        {activeTab === 'dashboard' && (
          <div>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Toplam Destinasyon</div>
                <div className="stat-value">{stats.totalDestinations}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Toplam Sohbet</div>
                <div className="stat-value">{stats.totalChats}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Ortalama Puan</div>
                <div className="stat-value">{stats.avgRating.toFixed(1)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">En Popüler Kategori</div>
                <div className="stat-value">
                  {Object.keys(stats.topCategory)[0] || 'N/A'}
                </div>
              </div>
            </div>

            <div className="table-container">
              <h2>Son Aktiviteler</h2>
              <table>
                <thead>
                  <tr>
                    <th>Zaman</th>
                    <th>Kullanıcı Sorusu</th>
                    <th>Sistem Cevabı</th>
                  </tr>
                </thead>
                <tbody>
                  {chatHistory.slice(0, 5).map((chat, index) => (
                    <tr key={index}>
                      <td>{new Date(chat.timestamp).toLocaleString('tr-TR')}</td>
                      <td>{chat.message.substring(0, 50)}...</td>
                      <td>{chat.response.substring(0, 50)}...</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'destinations' && (
          <div className="table-container">
            <h2>Tüm Destinasyonlar</h2>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>İsim</th>
                  <th>Kategori</th>
                  <th>Lokasyon</th>
                  <th>Puan</th>
                  <th>Etiketler</th>
                </tr>
              </thead>
              <tbody>
                {destinations.map((dest) => (
                  <tr key={dest.id}>
                    <td>{dest.id}</td>
                    <td>{dest.name}</td>
                    <td>{dest.category}</td>
                    <td>{dest.location}</td>
                    <td>{dest.rating}</td>
                    <td>{dest.tags.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'add-destination' && (
          <div className="form-container">
            <h2>Yeni Destinasyon Ekle</h2>
            <form onSubmit={(e) => {
              e.preventDefault();
              // API call would go here
              console.log('New destination:', newDestination);
              alert('Destinasyon eklendi! (Demo - gerçek API bağlantısı gerekli)');
            }}>
              <div className="form-group">
                <label className="form-label">İsim</label>
                <input
                  type="text"
                  className="form-input"
                  value={newDestination.name}
                  onChange={(e) => setNewDestination({...newDestination, name: e.target.value})}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Açıklama</label>
                <textarea
                  className="form-input"
                  value={newDestination.description}
                  onChange={(e) => setNewDestination({...newDestination, description: e.target.value})}
                  rows={3}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Kategori</label>
                <select
                  className="form-input"
                  value={newDestination.category}
                  onChange={(e) => setNewDestination({...newDestination, category: e.target.value})}
                  required
                >
                  <option value="">Seçiniz</option>
                  <option value="Tarihi">Tarihi</option>
                  <option value="Dini">Dini</option>
                  <option value="Müze">Müze</option>
                  <option value="Doğa">Doğa</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Lokasyon</label>
                <input
                  type="text"
                  className="form-input"
                  value={newDestination.location}
                  onChange={(e) => setNewDestination({...newDestination, location: e.target.value})}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Puan (1-5)</label>
                <input
                  type="number"
                  className="form-input"
                  min="1"
                  max="5"
                  step="0.1"
                  value={newDestination.rating}
                  onChange={(e) => setNewDestination({...newDestination, rating: parseFloat(e.target.value)})}
                  required
                />
              </div>

              <button type="submit" className="btn">Destinasyon Ekle</button>
            </form>
          </div>
        )}

        {activeTab === 'chats' && (
          <div className="table-container">
            <h2>Sohbet Geçmişi</h2>
            {chatHistory.map((chat, index) => (
              <div key={index} className="chat-message">
                <div className="message-user">👤 Kullanıcı: {chat.message}</div>
                <div className="message-bot">🤖 Asistan: {chat.response}</div>
                <div className="message-time">⏰ {new Date(chat.timestamp).toLocaleString('tr-TR')}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
