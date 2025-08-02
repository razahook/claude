import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Terminal Chat Interface Component
const TerminalChat = ({ sessionId, wsEndpoint, onScreenshotUpdate, onBrowserToggle, onProjectCreated }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history
    if (sessionId) {
      loadChatHistory();
    }
  }, [sessionId]);

  const loadChatHistory = async () => {
    try {
      const response = await fetch(`${API}/chat-history/${sessionId}`);
      if (response.ok) {
        const history = await response.json();
        setMessages(history.map(msg => ({
          type: 'user',
          content: msg.message,
          timestamp: new Date(msg.timestamp),
          response: msg.response,
          screenshot: msg.screenshot,
          needsBrowser: msg.browser_action !== null,
          projectCreated: msg.project_created
        })));
      }
    } catch (error) {
      console.error("Error loading chat history:", error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setInput("");

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage.content,
          ws_endpoint: wsEndpoint
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        setMessages(prev => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg.type === 'user') {
            lastMsg.response = data.response;
            lastMsg.screenshot = data.screenshot;
            lastMsg.needsBrowser = data.needs_browser || data.browser_action !== null;
            lastMsg.projectCreated = data.project_created;
          }
          return updated;
        });

        // Update screenshot in browser view
        if (data.screenshot && onScreenshotUpdate) {
          onScreenshotUpdate(data.screenshot);
        }

        // Toggle browser view based on needs_browser
        if (onBrowserToggle) {
          onBrowserToggle(data.needs_browser || data.browser_action !== null);
        }

        // Notify parent about project creation
        if (data.project_created && onProjectCreated) {
          onProjectCreated(data.project_created);
        }
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.type === 'user') {
          lastMsg.response = "Error: Failed to send message. Please try again.";
        }
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="terminal-chat">
      <div className="terminal-header">
        <div className="terminal-title">
          <span className="terminal-icon">$</span>
          AI Full-Stack Developer
        </div>
        <div className="session-info">
          Session: {sessionId?.substring(0, 8) || 'Not Connected'}
        </div>
      </div>
      
      <div className="terminal-body">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <span className="prompt">$</span> Welcome to AI Full-Stack Developer Terminal
              <br/>
              <span className="prompt">$</span> I can create complete applications and browse the web.
              <br/>
              <span className="prompt">$</span> Try: "Create a todo app" or "Go to google.com"
              <br/>
              <span className="prompt">$</span> Browser view appears when web browsing is needed.
            </div>
          )}
          
          {messages.map((msg, index) => (
            <div key={index} className="message-group">
              <div className="user-message">
                <span className="prompt user-prompt">user@terminal:~$</span>
                <span className="message-content">{msg.content}</span>
                <span className="timestamp">{msg.timestamp.toLocaleTimeString()}</span>
                {msg.needsBrowser && <span className="browser-badge">🌐</span>}
                {msg.projectCreated && <span className="project-badge">🚀</span>}
              </div>
              
              {msg.response && (
                <div className="ai-response">
                  <span className="prompt ai-prompt">ai@developer:~$</span>
                  <span className="message-content">{msg.response}</span>
                </div>
              )}

              {msg.projectCreated && (
                <div className="project-info">
                  <div className="project-header">
                    <span className="project-icon">📁</span>
                    <span className="project-name">{msg.projectCreated.project_name}</span>
                  </div>
                  <div className="project-details">
                    <div className="project-meta">
                      <span>ID: {msg.projectCreated.project_id}</span>
                      <span>Template: {msg.projectCreated.template}</span>
                      <span>Files: {msg.projectCreated.files_created?.length || 0}</span>
                    </div>
                    {msg.projectCreated.sandbox_urls && (
                      <div className="sandbox-urls">
                        {Object.entries(msg.projectCreated.sandbox_urls).map(([key, url]) => (
                          <a key={key} href={url} target="_blank" rel="noopener noreferrer" className="sandbox-link">
                            {key}: {url}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="loading-message">
              <span className="prompt ai-prompt">ai@developer:~$</span>
              <span className="loading-dots">Processing your request...</span>
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
            placeholder="Ask me to create apps or browse the web..."
            disabled={loading}
            className="terminal-text-input"
          />
          <button 
            onClick={sendMessage} 
            disabled={loading || !input.trim()}
            className="send-button"
          >
            ▶
          </button>
        </div>
      </div>
    </div>
  );
};

// Browser View Component
const BrowserView = ({ wsEndpoint, screenshot }) => {
  const [status, setStatus] = useState('disconnected');

  useEffect(() => {
    if (wsEndpoint) {
      setStatus('connected');
    } else {
      setStatus('disconnected');
    }
  }, [wsEndpoint]);

  return (
    <div className="browser-view">
      <div className="browser-header">
        <div className="browser-controls">
          <div className="control-dot red"></div>
          <div className="control-dot yellow"></div>
          <div className="control-dot green"></div>
        </div>
        <div className="browser-title">
          Browser View - {status === 'connected' ? 'Connected' : 'Disconnected'}
        </div>
        <div className={`status-indicator ${status}`}>
          <div className="status-dot"></div>
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
            <div className="placeholder-icon">🖥️</div>
            <div className="placeholder-text">
              {status === 'connected' 
                ? 'Waiting for browser interaction...' 
                : 'Create a browser session to see live view'
              }
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Main App Component
export default function App() {
  const [sessionId, setSessionId] = useState("");
  const [wsEndpoint, setWsEndpoint] = useState("");
  const [screenshot, setScreenshot] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    // Generate session ID on mount
    setSessionId(generateSessionId());
  }, []);

  const generateSessionId = () => {
    return 'session_' + Math.random().toString(36).substr(2, 9);
  };

  const createSession = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API}/create-session`, { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setWsEndpoint(data.wsEndpoint);
    } catch (e) {
      console.error("Error creating session:", e);
      setError("Failed to create browser session. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const endSession = () => {
    setWsEndpoint("");
    setScreenshot(null);
    setSessionId(generateSessionId());
    setShowBrowser(false);
    setProjects([]);
  };

  const handleScreenshotUpdate = (newScreenshot) => {
    setScreenshot(newScreenshot);
  };

  const handleBrowserToggle = (needsBrowser) => {
    setShowBrowser(needsBrowser);
  };

  const handleProjectCreated = (projectData) => {
    setProjects(prev => [...prev, projectData]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <div className="app-title">
          <span className="title-icon">⚡</span>
          AI Full-Stack Developer
        </div>
        <div className="header-info">
          {projects.length > 0 && (
            <div className="project-count">
              <span className="project-icon">🚀</span>
              {projects.length} project{projects.length !== 1 ? 's' : ''}
            </div>
          )}
          <div className="session-controls">
            {!wsEndpoint ? (
              <button 
                className="control-btn start-session" 
                onClick={createSession}
                disabled={loading}
              >
                {loading ? "Starting..." : "Start Session"}
              </button>
            ) : (
              <button 
                className="control-btn end-session" 
                onClick={endSession}
              >
                End Session
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button className="error-close" onClick={() => setError(null)}>×</button>
        </div>
      )}

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
                {project.sandbox_urls && Object.keys(project.sandbox_urls).length > 0 && (
                  <span className="project-status">🟢 Deployed</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={`app-body ${showBrowser ? 'split-view' : 'chat-only'}`}>
        <div className="chat-panel">
          <TerminalChat 
            sessionId={sessionId}
            wsEndpoint={wsEndpoint}
            onScreenshotUpdate={handleScreenshotUpdate}
            onBrowserToggle={handleBrowserToggle}
            onProjectCreated={handleProjectCreated}
          />
        </div>
        
        {showBrowser && (
          <div className="browser-panel">
            <BrowserView 
              wsEndpoint={wsEndpoint}
              screenshot={screenshot}
            />
          </div>
        )}
      </div>
    </div>
  );
}