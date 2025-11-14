// pages/index.tsx - Main chat interface
import React, { useState, useEffect, useRef } from 'react';

interface Message {
  text: string;
  isBot: boolean;
  timestamp: Date;
}

interface Destination {
  id: number;
  name: string;
  description: string;
  category: string;
  location: string;
  rating: number;
  image_url: string;
  tags: string[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { text: "Merhaba! Ben Mezopotamya turizm asistanınızım. Size nasıl yardımcı olabilirim?", isBot: true, timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [showDestinations, setShowDestinations] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const userId = typeof window !== 'undefined' ? 
    localStorage.getItem('userId') || `user_${Math.random().toString(36).substr(2, 9)}` : 
    'guest';

  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('userId')) {
      localStorage.setItem('userId', userId);
    }
    fetchDestinations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchDestinations = async () => {
    try {
      const response = await fetch('http://localhost:8000/destinations');
      const data = await response.json();
      setDestinations(data);
    } catch (error) {
      console.error('Error fetching destinations:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      text: input,
      isBot: false,
      timestamp: new Date()
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          message: input,
          language: 'tr'
        }),
      });

      const data = await response.json();
      
      const botMessage: Message = {
        text: data.response,
        isBot: true,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        text: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
        isBot: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const getRecommendations = async (interests: string[]) => {
    try {
      const response = await fetch('http://localhost:8000/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          interests: interests,
          max_results: 5
        }),
      });

      const data = await response.json();
      return data.recommendations;
    } catch (error) {
      console.error('Error getting recommendations:', error);
      return [];
    }
  };

  const quickActions = [
    { text: "Göbeklitepe hakkında bilgi", icon: "🏛️" },
    { text: "Bugün nereyi gezebilirim?", icon: "🗺️" },
    { text: "En iyi restoranlar", icon: "🍴" },
    { text: "Konaklama önerileri", icon: "🏨" }
  ];

  return (
    <div className="app-container">
      <style jsx>{`
        .app-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
        }

        .header {
          text-align: center;
          color: white;
          margin-bottom: 30px;
        }

        .header h1 {
          font-size: 2.5rem;
          margin-bottom: 10px;
        }

        .header p {
          font-size: 1.1rem;
          opacity: 0.9;
        }

        .main-content {
          display: grid;
          grid-template-columns: 1fr 300px;
          gap: 20px;
          height: 600px;
        }

        .chat-container {
          background: white;
          border-radius: 20px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          background: #f7f7f7;
        }

        .message {
          display: flex;
          margin-bottom: 15px;
        }

        .message.user {
          justify-content: flex-end;
        }

        .message-bubble {
          max-width: 70%;
          padding: 12px 18px;
          border-radius: 18px;
          word-wrap: break-word;
        }

        .message.bot .message-bubble {
          background: white;
          color: #333;
          box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .message.user .message-bubble {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .input-container {
          padding: 20px;
          background: white;
          border-top: 1px solid #e0e0e0;
        }

        .input-wrapper {
          display: flex;
          gap: 10px;
          margin-bottom: 15px;
        }

        .input-field {
          flex: 1;
          padding: 12px;
          border: 2px solid #e0e0e0;
          border-radius: 25px;
          font-size: 16px;
          outline: none;
          transition: border-color 0.3s;
        }

        .input-field:focus {
          border-color: #667eea;
        }

        .send-button {
          padding: 12px 25px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 25px;
          font-size: 16px;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .send-button:hover {
          transform: scale(1.05);
        }

        .send-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .quick-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .quick-action {
          padding: 8px 12px;
          background: #f0f0f0;
          border: none;
          border-radius: 15px;
          cursor: pointer;
          font-size: 14px;
          transition: background 0.3s;
        }

        .quick-action:hover {
          background: #e0e0e0;
        }

        .sidebar {
          background: white;
          border-radius: 20px;
          padding: 20px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          overflow-y: auto;
        }

        .destination-card {
          background: #f9f9f9;
          border-radius: 10px;
          padding: 15px;
          margin-bottom: 15px;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .destination-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .destination-name {
          font-weight: bold;
          color: #333;
          margin-bottom: 5px;
        }

        .destination-location {
          color: #666;
          font-size: 14px;
        }

        .destination-rating {
          color: #ffa500;
          font-size: 14px;
          margin-top: 5px;
        }

        .loading-indicator {
          display: flex;
          justify-content: center;
          padding: 10px;
        }

        .loading-dots {
          display: flex;
          gap: 5px;
        }

        .dot {
          width: 10px;
          height: 10px;
          background: #667eea;
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out both;
        }

        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        .dot:nth-child(3) { animation-delay: 0; }

        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }

        @media (max-width: 768px) {
          .main-content {
            grid-template-columns: 1fr;
          }
          
          .sidebar {
            display: none;
          }
        }
      `}</style>

      <div className="header">
        <h1>🏛️ Mezopotamya.Travel</h1>
        <p>Tarihin beşiği GAP bölgesinde unutulmaz bir yolculuğa hazır mısınız?</p>
      </div>

      <div className="main-content">
        <div className="chat-container">
          <div className="messages-container">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.isBot ? 'bot' : 'user'}`}>
                <div className="message-bubble">
                  {message.text}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="loading-indicator">
                <div className="loading-dots">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-container">
            <div className="input-wrapper">
              <input
                type="text"
                className="input-field"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Sorunuzu yazın..."
                disabled={isLoading}
              />
              <button 
                className="send-button" 
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
              >
                Gönder
              </button>
            </div>

            <div className="quick-actions">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  className="quick-action"
                  onClick={() => {
                    setInput(action.text);
                    sendMessage();
                  }}
                >
                  {action.icon} {action.text}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar">
          <h3 style={{marginBottom: '15px', color: '#333'}}>Popüler Yerler</h3>
          {destinations.slice(0, 5).map((dest) => (
            <div key={dest.id} className="destination-card">
              <div className="destination-name">{dest.name}</div>
              <div className="destination-location">📍 {dest.location}</div>
              <div className="destination-rating">⭐ {dest.rating}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
