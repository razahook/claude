import React, { useState } from "react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Custom Browser UI Component
const BrowserUI = ({ wsUrl }) => {
  return (
    <div className="browser-container">
      <div className="browser-header">
        <div className="browser-controls">
          <div className="control-dot red"></div>
          <div className="control-dot yellow"></div>
          <div className="control-dot green"></div>
        </div>
        <div className="browser-title">Live Browser Session</div>
      </div>
      <div className="browser-content">
        {wsUrl ? (
          <div className="browser-status">
            <div className="status-indicator active"></div>
            <p>Browser session active</p>
            <p className="ws-url">WebSocket: {wsUrl.substring(0, 50)}...</p>
          </div>
        ) : (
          <div className="browser-status">
            <div className="status-indicator inactive"></div>
            <p>No active session</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default function App() {
  const [wsEndpoint, setWsEndpoint] = useState("");
  const [url, setUrl] = useState("");
  const [extracted, setExtracted] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function createSession() {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API}/create-session`, { 
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
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
  }

  async function runTask() {
    if (!url.trim()) {
      setError("Please enter a URL to scrape");
      return;
    }

    setLoading(true);
    setError(null);
    setExtracted(null);

    try {
      const response = await fetch(`${API}/run-task`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json" 
        },
        body: JSON.stringify({ 
          wsEndpoint: wsEndpoint, 
          targetUrl: url 
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setExtracted(data.extracted);
    } catch (e) {
      console.error("Error running task:", e);
      setError("Failed to run scraping task. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="container">
        <h1 className="title">🤖 Agentic Scraper Demo</h1>
        <p className="subtitle">AI-powered browser automation with live session view</p>

        {/* Session Management */}
        <div className="section">
          <h2>Browser Session</h2>
          {!wsEndpoint ? (
            <button 
              className="btn btn-primary" 
              onClick={createSession}
              disabled={loading}
            >
              {loading ? "Creating Session..." : "🚀 Start Browser Session"}
            </button>
          ) : (
            <div className="session-info">
              <span className="status-badge active">Session Active</span>
              <button 
                className="btn btn-secondary" 
                onClick={() => {
                  setWsEndpoint("");
                  setExtracted(null);
                  setUrl("");
                }}
              >
                End Session
              </button>
            </div>
          )}
        </div>

        {/* Live Browser UI */}
        {wsEndpoint && (
          <div className="section">
            <h2>Live Browser View</h2>
            <BrowserUI wsUrl={wsEndpoint} />
          </div>
        )}

        {/* Task Input */}
        {wsEndpoint && (
          <div className="section">
            <h2>Scraping Task</h2>
            <div className="input-group">
              <input
                type="text"
                placeholder="Enter URL to scrape (e.g., https://example.com)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="url-input"
                disabled={loading}
              />
              <button 
                className="btn btn-primary" 
                onClick={runTask}
                disabled={loading || !url.trim()}
              >
                {loading ? "Running..." : "🔍 Run AI Scraping"}
              </button>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="section">
            <div className="error-box">
              ⚠️ {error}
            </div>
          </div>
        )}

        {/* Results */}
        {extracted && (
          <div className="section">
            <h2>📊 Extracted Content</h2>
            <div className="results-container">
              <div className="result-item">
                <h3>Page Title</h3>
                <p className="extracted-content">{extracted.title || "N/A"}</p>
              </div>
              <div className="result-item">
                <h3>First Paragraph</h3>
                <p className="extracted-content">{extracted.p || "N/A"}</p>
              </div>
              <details className="raw-data">
                <summary>Raw Data</summary>
                <pre>{JSON.stringify(extracted, null, 2)}</pre>
              </details>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="footer">
          <p>Powered by Browserless, OpenAI GPT-4o-mini, and Playwright</p>
        </div>
      </div>
    </div>
  );
}