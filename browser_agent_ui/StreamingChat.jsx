import React, { useState, useEffect, useRef } from 'react';
import './StreamingChat.css';

const StreamingChat = ({ 
  websocketUrl, 
  onMessage, 
  defaultProvider = 'openai', 
  defaultModel = 'gpt-4' 
}) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [browserSession, setBrowserSession] = useState(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [projects, setProjects] = useState([]);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      wsRef.current = new WebSocket(websocketUrl);
      
      wsRef.current.onopen = () => {
        setConnected(true);
        console.log('WebSocket connected');
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };
      
      wsRef.current.onclose = () => {
        setConnected(false);
        console.log('WebSocket disconnected');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [websocketUrl]);

  const handleWebSocketMessage = (data) => {
    if (data.type === 'ai_response') {
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg && lastMsg.type === 'user') {
          lastMsg.response = data.content;
          lastMsg.provider = data.provider;
          lastMsg.model = data.model;
          lastMsg.browser_action = data.browser_action;
          lastMsg.screenshot = data.screenshot;
          lastMsg.project_created = data.project_created;
          lastMsg.needs_browser = data.needs_browser;
        }
        return updated;
      });
      setLoading(false);
      
      // Handle browser view toggle
      if (data.needs_browser) {
        setShowBrowser(true);
      }
      
      // Handle project creation
      if (data.project_created) {
        setProjects(prev => [...prev, data.project_created]);
      }
    }
    
    if (onMessage) {
      onMessage(data);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading || !connected) return;

    const userMessage = {
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
      id: Date.now().toString()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setInput('');

    // Send message via WebSocket
    const messagePayload = {
      type: 'chat_message',
      content: userMessage.content,
      provider: defaultProvider,
      model: defaultModel,
      use_agents: true,
      session_id: browserSession?.sessionId || 'default'
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(messagePayload));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderMessage = (content) => {
    return content.split('\n').map((line, index) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return <div key={index} className="message-header">{line.slice(2, -2)}</div>;
      } else if (line.startsWith('- ') || line.startsWith('• ')) {
        return <div key={index} className="message-bullet">• {line.slice(2)}</div>;
      } else if (line.startsWith('```')) {
        return <div key={index} className="message-code">```</div>;
      } else if (line.trim() === '') {
        return <br key={index} />;
      } else {
        return <div key={index} className="message-line">{line}</div>;
      }
    });
  };

  const BrowserView = ({ screenshot, browserAction }) => (
    <div className="browser-view">
      <div className="browser-header">
        <div className="browser-controls">
          <div className="control-dot red"></div>
          <div className="control-dot yellow"></div>
          <div className="control-dot green"></div>
        </div>
        <div className="browser-title">
          🔴 Live Browser Automation
          <span className="connection-status connected">● Live</span>
        </div>
        <div className="browser-controls-right">
          <button className="minimize-btn" onClick={() => setShowBrowser(false)}>
            Minimize
          </button>
        </div>
      </div>
      
      <div className="browser-content">
        {screenshot ? (
          <img 
            src={`data:image/png;base64,${screenshot}`} 
            alt="Browser Screenshot"
            className="browser-screenshot"
          />
        ) : (
          <div className="browser-placeholder">
            <div className="placeholder-icon">🌐</div>
            <div className="placeholder-text">
              Real-time browser automation ready
              <br />
              Browser actions will appear here automatically
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="streaming-chat">
      <div className="chat-header">
        <div className="header-left">
          <span className="terminal-icon">⚡</span>
          <h1>AI Full-Stack Developer + Browser-Use</h1>
        </div>
        <div className="header-right">
          {projects.length > 0 && (
            <div className="project-count">
              <span className="project-icon">🚀</span>
              {projects.length} project{projects.length !== 1 ? 's' : ''}
            </div>
          )}
          <div className="connection-indicator">
            <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></span>
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {projects.length > 0 && (
        <div className="projects-bar">
          <div className="projects-header">
            <span className="projects-title">Created Projects:</span>
          </div>
          <div className="projects-list">
            {projects.map((project, index) => (
              <div key={index} className="project-item">
                <span className="project-name">{project.project_name}</span>
                <span className="project-template">{project.template}</span>
                <span className="project-status">🟢 Ready</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={`chat-body ${showBrowser ? 'split-view' : 'full-view'}`}>
        <div className="chat-panel">
          <div className="terminal-container">
            <div className="terminal-header">
              <div className="terminal-title">
                <span className="terminal-prompt">$</span>
                AI Full-Stack Developer + Browser-Use
              </div>
              <div className="session-info">
                Session: {browserSession?.sessionId?.substring(0, 8) || 'Auto-Started'}
              </div>
            </div>
            
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="welcome-message">
                  <span className="prompt">$</span> Welcome to AI Full-Stack Developer with Auto-Browser
                  <br />
                  <span className="prompt">$</span> ✨ Browser automation starts automatically - no buttons needed!
                  <br />
                  <span className="prompt">$</span> Try: "Create a todo app" or "Go to google.com and take screenshot"
                  <br />
                  <span className="prompt">$</span> 🔴 Watch me work live in the embedded browser view!
                </div>
              )}
              
              {messages.map((msg, index) => (
                <div key={msg.id || index} className="message-group">
                  <div className="user-message">
                    <span className="prompt user-prompt">user@terminal:~$</span>
                    <span className="message-content">{msg.content}</span>
                    <span className="timestamp">{msg.timestamp.toLocaleTimeString()}</span>
                    {msg.needs_browser && <span className="browser-badge">🌐</span>}
                    {msg.project_created && <span className="project-badge">🚀</span>}
                  </div>
                  
                  {msg.response && (
                    <div className="ai-response">
                      <span className="prompt ai-prompt">ai@developer:~$</span>
                      <div className="message-content enhanced">
                        {renderMessage(msg.response)}
                      </div>
                      {msg.provider && (
                        <div className="response-meta">
                          <span className="provider-badge">{msg.provider}</span>
                          <span className="model-badge">{msg.model}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {msg.project_created && (
                    <div className="project-info">
                      <div className="project-header">
                        <span className="project-icon">📁</span>
                        <span className="project-name">{msg.project_created.project_name}</span>
                      </div>
                      <div className="project-details">
                        <div className="project-meta">
                          <span>Template: {msg.project_created.template}</span>
                          <span>Files: {msg.project_created.files_created?.length || 0}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              
              {loading && (
                <div className="loading-message">
                  <span className="prompt ai-prompt">ai@developer:~$</span>
                  <span className="loading-dots">Processing your request with real-time automation...</span>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
            
            <div className="terminal-input">
              <span className="prompt input-prompt">user@terminal:~$</span>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me to create apps or browse the web in real-time..."
                disabled={loading || !connected}
                className="terminal-text-input"
              />
              <button 
                onClick={sendMessage} 
                disabled={loading || !input.trim() || !connected}
                className="send-button"
              >
                ▶
              </button>
            </div>
          </div>
        </div>
        
        {showBrowser && (
          <div className="browser-panel">
            <BrowserView 
              screenshot={messages[messages.length - 1]?.screenshot}
              browserAction={messages[messages.length - 1]?.browser_action}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default StreamingChat;