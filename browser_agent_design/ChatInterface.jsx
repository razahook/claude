import React from 'react';
import './ChatInterface.css';

const ChatInterface = ({
  // Your existing state variables
  messages,
  connected,
  currentProvider,
  currentModel,
  loading,
  inputValue,
  
  // Your existing handlers
  sendMessage,
  handleKeyPress,
  handleInputChange,
  
  // Optional additional props you might have
  projects = [],
  sessionId = null,
  showBrowser = false,
  currentOutput = null, // For code/browser output
  
  // Provider controls (if you have them)
  availableProviders = ['openai', 'claude', 'gemini'],
  availableModels = ['gpt-4', 'gpt-3.5-turbo', 'claude-3'],
  onProviderChange,
  onModelChange
}) => {

  const renderMessage = (content) => {
    if (!content) return null;
    
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
    <div className="chat-interface">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <span className="terminal-icon">⚡</span>
          <h1>AI Full-Stack Developer + Browser-Use</h1>
        </div>
        <div className="header-right">
          {projects && projects.length > 0 && (
            <div className="project-count">
              <span className="project-icon">🚀</span>
              {projects.length} project{projects.length !== 1 ? 's' : ''}
            </div>
          )}
          
          {/* Provider Controls */}
          <div className="provider-controls">
            <select 
              value={currentProvider} 
              onChange={onProviderChange}
              className="provider-select"
              disabled={loading}
            >
              {availableProviders.map(provider => (
                <option key={provider} value={provider}>
                  {provider.charAt(0).toUpperCase() + provider.slice(1)}
                </option>
              ))}
            </select>
            
            <select 
              value={currentModel} 
              onChange={onModelChange}
              className="model-select"
              disabled={loading}
            >
              {availableModels.map(model => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
          
          <div className="connection-indicator">
            <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></span>
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* Projects Bar */}
      {projects && projects.length > 0 && (
        <div className="projects-bar">
          <div className="projects-header">
            <span className="projects-title">Created Projects:</span>
          </div>
          <div className="projects-list">
            {projects.map((project, index) => (
              <div key={index} className="project-item">
                <span className="project-name">{project.name}</span>
                <span className="project-template">{project.template || project.type}</span>
                <span className="project-status">🟢 Ready</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`chat-body ${showBrowser || currentOutput ? 'split-view' : 'full-view'}`}>
        
        {/* Left Panel - Chat */}
        <div className="chat-panel">
          <div className="terminal-container">
            <div className="terminal-header">
              <div className="terminal-title">
                <span className="terminal-prompt">$</span>
                AI Full-Stack Developer + Browser-Use
              </div>
              <div className="session-info">
                Session: {sessionId ? sessionId.substring(0, 8) : 'Auto-Started'}
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
                    <span className="message-content">{msg.content || msg.message}</span>
                    <span className="timestamp">
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                    </span>
                    {msg.needsBrowser && <span className="browser-badge">🌐</span>}
                    {msg.projectCreated && <span className="project-badge">🚀</span>}
                  </div>
                  
                  {msg.response && (
                    <div className="ai-response">
                      <span className="prompt ai-prompt">ai@developer:~$</span>
                      <div className="message-content enhanced">
                        {renderMessage(msg.response)}
                      </div>
                      <div className="response-meta">
                        <span className="provider-badge">{msg.provider || currentProvider}</span>
                        <span className="model-badge">{msg.model || currentModel}</span>
                      </div>
                    </div>
                  )}

                  {msg.projectCreated && (
                    <div className="project-info">
                      <div className="project-header">
                        <span className="project-icon">📁</span>
                        <span className="project-name">
                          {msg.projectCreated.name || msg.projectCreated.project_name}
                        </span>
                      </div>
                      <div className="project-details">
                        <div className="project-meta">
                          <span>Template: {msg.projectCreated.template}</span>
                          <span>Files: {msg.projectCreated.files?.length || 0}</span>
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
            </div>
            
            <div className="terminal-input">
              <span className="prompt input-prompt">user@terminal:~$</span>
              <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="Ask me to create apps or browse the web in real-time..."
                disabled={loading || !connected}
                className="terminal-text-input"
              />
              <button 
                onClick={sendMessage} 
                disabled={loading || !inputValue?.trim() || !connected}
                className="send-button"
              >
                ▶
              </button>
            </div>
          </div>
        </div>
        
        {/* Right Panel - Browser/Code Output */}
        {(showBrowser || currentOutput) && (
          <div className="output-panel">
            <div className="output-view">
              <div className="output-header">
                <div className="output-controls">
                  <div className="control-dot red"></div>
                  <div className="control-dot yellow"></div>
                  <div className="control-dot green"></div>
                </div>
                <div className="output-title">
                  {currentOutput?.type === 'browser' && '🔴 Live Browser Automation'}
                  {currentOutput?.type === 'code' && '💻 Code Execution'}
                  {currentOutput?.type === 'file' && '📁 File Output'}
                  {!currentOutput?.type && '🌐 Real-Time Output'}
                  <span className="connection-status connected">● Live</span>
                </div>
                <div className="output-controls-right">
                  <button className="minimize-btn" onClick={() => {}}>
                    Minimize
                  </button>
                </div>
              </div>
              
              <div className="output-content">
                {/* Browser Screenshot */}
                {currentOutput?.type === 'browser' && currentOutput?.screenshot && (
                  <img 
                    src={`data:image/png;base64,${currentOutput.screenshot}`} 
                    alt="Browser Screenshot"
                    className="browser-screenshot"
                  />
                )}
                
                {/* Code Output */}
                {currentOutput?.type === 'code' && (
                  <div className="code-output">
                    <pre className="code-block">
                      <code>{currentOutput.content}</code>
                    </pre>
                  </div>
                )}
                
                {/* File Content */}
                {currentOutput?.type === 'file' && (
                  <div className="file-output">
                    <div className="file-header">
                      <span className="file-name">{currentOutput.filename}</span>
                      <span className="file-size">{currentOutput.size || 'Unknown size'}</span>
                    </div>
                    <pre className="file-content">
                      <code>{currentOutput.content}</code>
                    </pre>
                  </div>
                )}
                
                {/* Default Placeholder */}
                {!currentOutput && (
                  <div className="output-placeholder">
                    <div className="placeholder-icon">🌐</div>
                    <div className="placeholder-text">
                      Real-time browser automation ready
                      <br />
                      Browser actions and code output will appear here automatically
                    </div>
                  </div>
                )}
                
                {/* Generic Output */}
                {currentOutput && !['browser', 'code', 'file'].includes(currentOutput.type) && (
                  <div className="generic-output">
                    <pre>{JSON.stringify(currentOutput, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;