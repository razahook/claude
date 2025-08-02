import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Enhanced Terminal Chat Interface Component
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
          projectCreated: msg.project_created,
          browserUseResult: msg.browser_use_result,
          vncUrl: msg.vnc_url,
          conversationContinues: msg.conversation_continues !== false
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
          ws_endpoint: wsEndpoint,
          use_browser_use: true
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
            lastMsg.browserUseResult = data.browser_use_result;
            lastMsg.vncUrl = data.vnc_url;
            lastMsg.conversationContinues = data.conversation_continues !== false;
          }
          return updated;
        });

        // Update screenshot in browser view
        if (data.screenshot && onScreenshotUpdate) {
          onScreenshotUpdate(data.screenshot);
        }

        // Toggle browser view based on needs_browser or browser_use_result
        if (onBrowserToggle) {
          const showBrowser = data.needs_browser || data.browser_use_result || data.browser_action !== null;
          onBrowserToggle(showBrowser);
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
          lastMsg.conversationContinues = true;
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

  const renderMessage = (content) => {
    // Enhanced markdown-like rendering for better conversation flow
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

  return (
    <div className="terminal-chat">
      <div className="terminal-header">
        <div className="terminal-title">
          <span className="terminal-icon">$</span>
          AI Full-Stack Developer + Browser-Use
        </div>
        <div className="session-info">
          Session: {sessionId?.substring(0, 8) || 'Not Connected'}
        </div>
      </div>
      
      <div className="terminal-body">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <span className="prompt">$</span> Welcome to AI Full-Stack Developer with Real-Time Browser
              <br/>
              <span className="prompt">$</span> I can create complete applications and browse the web in real-time.
              <br/>
              <span className="prompt">$</span> Try: "Create a todo app" or "Go to apex legends stats and extract data"
              <br/>
              <span className="prompt">$</span> Watch me work live with VNC viewer!
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
                {msg.browserUseResult && <span className="browser-use-badge">🔴</span>}
              </div>
              
              {msg.response && (
                <div className="ai-response">
                  <span className="prompt ai-prompt">ai@developer:~$</span>
                  <div className="message-content enhanced">
                    {renderMessage(msg.response)}
                  </div>
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

              {msg.browserUseResult && (
                <div className="browser-use-info">
                  <div className="browser-use-header">
                    <span className="browser-use-icon">🔴</span>
                    <span>Real-Time Browser Task</span>
                    <span className={`status ${msg.browserUseResult.success ? 'success' : 'error'}`}>
                      {msg.browserUseResult.success ? '✅ Success' : '❌ Error'}
                    </span>
                  </div>
                  {msg.vncUrl && (
                    <div className="vnc-link">
                      <a href={msg.vncUrl} target="_blank" rel="noopener noreferrer">
                        🖥️ Watch Live: {msg.vncUrl}
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="loading-message">
              <span className="prompt ai-prompt">ai@developer:~$</span>
              <span className="loading-dots">Processing your request with real-time browser automation...</span>
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

// Enhanced VNC Browser View Component with Auto-embed
const VNCBrowserView = ({ vnc_url, browser_use_result, wsEndpoint, autoShow = true }) => {
  const [isEmbedded, setIsEmbedded] = useState(autoShow);
  const [connectionStatus, setConnectionStatus] = useState('connecting');

  useEffect(() => {
    // Auto-show when browser actions are happening
    if (browser_use_result?.success || wsEndpoint) {
      setIsEmbedded(true);
    }
  }, [browser_use_result, wsEndpoint]);

  useEffect(() => {
    // Check connection status periodically
    const checkConnection = () => {
      if (wsEndpoint) {
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('disconnected');
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
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
          🔴 Live Browser Automation 
          <span className={`connection-status ${connectionStatus}`}>
            {connectionStatus === 'connected' ? '● Live' : '○ Standby'}
          </span>
        </div>
        <div className="vnc-controls">
          <button 
            className="vnc-toggle"
            onClick={() => setIsEmbedded(!isEmbedded)}
          >
            {isEmbedded ? 'Minimize' : 'Expand'}
          </button>
        </div>
      </div>
      
      <div className="browser-content">
        {isEmbedded ? (
          <div className="embedded-browser">
            {vnc_url && vnc_url !== "http://localhost:6080/vnc.html" ? (
              <iframe 
                src={vnc_url}
                className="browser-iframe"
                title="Live Browser Automation"
                allow="camera; microphone; display-capture"
              />
            ) : (
              <div className="browser-stream-placeholder">
                <div className="stream-icon">🌐</div>
                <div className="stream-status">
                  <h3>Real-Time Browser Automation</h3>
                  <p>
                    {connectionStatus === 'connected' 
                      ? '✅ Browser session active - AI actions will appear here automatically'
                      : '⏳ Initializing browser automation...'
                    }
                  </p>
                  {browser_use_result?.success && (
                    <div className="last-action">
                      <p><strong>Last Action:</strong> {browser_use_result.task}</p>
                      {browser_use_result.extracted_data && (
                        <details className="extracted-preview">
                          <summary>📊 Data Extracted</summary>
                          <pre>{JSON.stringify(browser_use_result.extracted_data, null, 2).slice(0, 200)}...</pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="browser-minimized">
            <div className="minimized-status">
              <span className="status-icon">🟢</span>
              <span>Browser automation running in background</span>
              <button onClick={() => setIsEmbedded(true)} className="expand-btn">
                Expand View
              </button>
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
  const [vncUrl, setVncUrl] = useState("http://localhost:6080/vnc.html");
  const [browserUseResult, setBrowserUseResult] = useState(null);

  useEffect(() => {
    // Generate session ID on mount
    setSessionId(generateSessionId());
    // Auto-start browser session for seamless experience
    autoStartSession();
    // Load VNC info
    loadVNCInfo();
  }, []);

  const autoStartSession = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API}/create-session`, { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      
      if (response.ok) {
        const data = await response.json();
        setWsEndpoint(data.wsEndpoint);
        console.log('Browser session auto-started:', data.sessionId);
      }
    } catch (e) {
      console.log('Auto-start session failed, will start manually when needed:', e.message);
    } finally {
      setLoading(false);
    }
  };

  const generateSessionId = () => {
    return 'session_' + Math.random().toString(36).substr(2, 9);
  };

  const loadVNCInfo = async () => {
    try {
      const response = await fetch(`${API}/vnc-info`);
      if (response.ok) {
        const vncInfo = await response.json();
        setVncUrl(vncInfo.vnc_url);
      }
    } catch (error) {
      console.error("Error loading VNC info:", error);
    }
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
    setBrowserUseResult(null);
  };

  const handleScreenshotUpdate = (newScreenshot) => {
    setScreenshot(newScreenshot);
  };

  const handleBrowserToggle = (needsBrowser, browserResult = null) => {
    setShowBrowser(needsBrowser);
    if (browserResult) {
      setBrowserUseResult(browserResult);
    }
  };

  const handleProjectCreated = (projectData) => {
    setProjects(prev => [...prev, projectData]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <div className="app-title">
          <span className="title-icon">⚡</span>
          AI Full-Stack Developer + Browser-Use
        </div>
        <div className="header-info">
          {projects.length > 0 && (
            <div className="project-count">
              <span className="project-icon">🚀</span>
              {projects.length} project{projects.length !== 1 ? 's' : ''}
            </div>
          )}
          <div className="vnc-info">
            <a href={vncUrl} target="_blank" rel="noopener noreferrer" className="vnc-link">
              🔴 Live Browser
            </a>
          </div>
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
            <VNCBrowserView 
              vnc_url={vncUrl}
              browser_use_result={browserUseResult}
            />
          </div>
        )}
      </div>
    </div>
  );
}