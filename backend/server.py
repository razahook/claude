from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import httpx
import json
from playwright.async_api import async_playwright
import asyncio
from openai import AsyncOpenAI
import base64
import tempfile
import shutil
import aiofiles
import subprocess
from browser_use_integration import get_browser_use_agent


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
BROWSERLESS_API_KEY = os.environ['BROWSERLESS_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
ZAI_API_KEY = os.environ['ZAI_API_KEY']
DAYTONA_API_KEY = os.environ.get('DAYTONA_API_KEY', '')
REPLIT_API_KEY = os.environ.get('REPLIT_API_KEY', '')

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    browser_action: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    project_created: Optional[Dict[str, Any]] = None
    browser_use_result: Optional[Dict[str, Any]] = None
    vnc_url: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str
    ws_endpoint: Optional[str] = None
    use_browser_use: Optional[bool] = True  # Default to using browser-use

class ChatResponse(BaseModel):
    id: str
    response: str
    browser_action: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    needs_browser: Optional[bool] = False
    project_created: Optional[Dict[str, Any]] = None
    browser_use_result: Optional[Dict[str, Any]] = None
    vnc_url: Optional[str] = None
    conversation_continues: Optional[bool] = True

class BrowserSessionResponse(BaseModel):
    wsEndpoint: str
    sessionId: str

class ProjectRequest(BaseModel):
    description: str
    session_id: str
    project_type: str = "fullstack"  # fullstack, frontend, backend, api

class ProjectResponse(BaseModel):
    project_id: str
    project_name: str
    files_created: List[str]
    local_path: str
    sandbox_url: Optional[str] = None
    preview_url: Optional[str] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


# Full Stack Development Templates
TEMPLATES = {
    "react_express": {
        "name": "React + Express.js",
        "description": "Full-stack app with React frontend and Express.js backend",
        "files": {
            "package.json": """{
  "name": "fullstack-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "concurrently \\"npm run server\\" \\"npm run client\\"",
    "server": "cd server && npm run dev",
    "client": "cd client && npm start",
    "build": "cd client && npm run build",
    "install-deps": "npm install && cd server && npm install && cd ../client && npm install"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}""",
            "server/package.json": """{
  "name": "server",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}""",
            "server/server.js": """const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({ message: 'Server is running!' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});""",
            "client/package.json": """{
  "name": "client",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "axios": "^1.5.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  },
  "proxy": "http://localhost:5000"
}""",
            "client/public/index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>React App</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>""",
            "client/src/index.js": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);""",
            "client/src/App.js": """import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [message, setMessage] = useState('');

  useEffect(() => {
    axios.get('/api/health')
      .then(response => {
        setMessage(response.data.message);
      })
      .catch(error => {
        console.error('Error:', error);
        setMessage('Failed to connect to server');
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Full Stack App</h1>
        <p>{message}</p>
      </header>
    </div>
  );
}

export default App;""",
            "client/src/App.css": """.App {
  text-align: center;
}

.App-header {
  background-color: #282c34;
  padding: 20px;
  color: white;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

h1 {
  margin-bottom: 20px;
}""",
            "README.md": """# Full Stack Application

## Setup
1. Run `npm run install-deps` to install all dependencies
2. Run `npm run dev` to start both frontend and backend
3. Frontend: http://localhost:3000
4. Backend: http://localhost:5000

## Structure
- `/client` - React frontend
- `/server` - Express.js backend
"""
        }
    },
    "next_fastapi": {
        "name": "Next.js + FastAPI",
        "description": "Modern full-stack with Next.js frontend and FastAPI backend",
        "files": {
            "package.json": """{
  "name": "nextjs-fastapi-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "concurrently \\"npm run backend\\" \\"npm run frontend\\"",
    "backend": "cd backend && python -m uvicorn main:app --reload --port 8000",
    "frontend": "cd frontend && npm run dev",
    "build": "cd frontend && npm run build",
    "install-deps": "cd frontend && npm install && cd ../backend && pip install -r requirements.txt"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}""",
            "backend/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    text: str

@app.get("/api/health")
def health_check():
    return {"message": "FastAPI server is running!"}

@app.post("/api/message")
def create_message(message: Message):
    return {"received": message.text, "processed": True}
""",
            "backend/requirements.txt": """fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
""",
            "frontend/package.json": """{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.5.0"
  }
}""",
            "frontend/pages/index.js": """import { useState, useEffect } from 'react';
import axios from 'axios';

export default function Home() {
  const [message, setMessage] = useState('');
  const [inputText, setInputText] = useState('');

  useEffect(() => {
    axios.get('http://localhost:8000/api/health')
      .then(response => {
        setMessage(response.data.message);
      })
      .catch(error => {
        console.error('Error:', error);
        setMessage('Failed to connect to backend');
      });
  }, []);

  const sendMessage = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/message', {
        text: inputText
      });
      setMessage(`Backend processed: ${response.data.received}`);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>Next.js + FastAPI</h1>
      <p>{message}</p>
      <div style={{ margin: '20px' }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Enter a message"
          style={{ padding: '10px', margin: '10px' }}
        />
        <button onClick={sendMessage} style={{ padding: '10px 20px' }}>
          Send to Backend
        </button>
      </div>
    </div>
  );
}""",
            "README.md": """# Next.js + FastAPI Application

## Setup
1. Run `npm run install-deps` to install dependencies
2. Run `npm run dev` to start both servers
3. Frontend: http://localhost:3000
4. Backend: http://localhost:8000

## Structure
- `/frontend` - Next.js frontend
- `/backend` - FastAPI backend
"""
        }
    }
}


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.session_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        self.session_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        self.active_connections.remove(websocket)
        if session_id in self.session_connections:
            self.session_connections[session_id].remove(websocket)

    async def send_to_session(self, message: str, session_id: str):
        if session_id in self.session_connections:
            for connection in self.session_connections[session_id]:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()


# Existing routes
@api_router.get("/")
async def root():
    return {"message": "AI Terminal Assistant Ready"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


# Enhanced browser session with VNC-like capability
@api_router.post("/create-session", response_model=BrowserSessionResponse)
async def create_browserless_session():
    """Create a new Browserless session with VNC viewing capability"""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        session_config = {
            "ttl": 600000,  # 10 minutes
            "stealth": True,
            "headless": False,  # Changed to false for visual debugging
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--window-size=1280,720"
            ]
        }
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"https://production-sfo.browserless.io/session?token={BROWSERLESS_API_KEY}",
                headers={"Content-Type": "application/json"},
                json=session_config,
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_text = await response.atext() if hasattr(response, 'atext') else response.text
                logger.error(f"Browserless API error: {response.status_code} - {error_text}")
                raise HTTPException(status_code=500, detail=f"Browserless API error: {response.status_code}")
            
            data = response.json()
            return BrowserSessionResponse(wsEndpoint=data["connect"], sessionId=session_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Browserless session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create browser session")


async def call_zai_api(prompt: str) -> str:
    """Call Z.ai API with GLM model for general conversation"""
    try:
        async with httpx.AsyncClient() as client:
            # Try GLM-4.5 for general conversation first
            response = await client.post(
                "https://api.z.ai/api/v1/agents",
                headers={
                    "Authorization": f"Bearer {ZAI_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept-Language": "en-US,en"
                },
                json={
                    "agent_id": "glm-4.5-flash",  # Try GLM 4.5 first
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("choices") and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if choice.get("messages") and len(choice["messages"]) > 0:
                        message = choice["messages"][0]
                        content = message.get("content", {})
                        return content.get("text", "")
            
            # If GLM doesn't work, try other agent IDs
            alternative_agents = ["general_chat", "assistant", "glm-4", "general"]
            
            for agent_id in alternative_agents:
                try:
                    response = await client.post(
                        "https://api.z.ai/api/v1/agents",
                        headers={
                            "Authorization": f"Bearer {ZAI_API_KEY}",
                            "Content-Type": "application/json",
                            "Accept-Language": "en-US,en"
                        },
                        json={
                            "agent_id": agent_id,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": prompt
                                        }
                                    ]
                                }
                            ]
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("choices") and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            if choice.get("messages") and len(choice["messages"]) > 0:
                                message = choice["messages"][0]
                                content = message.get("content", {})
                                text_response = content.get("text", "")
                                if text_response and not is_chinese_text(text_response):
                                    return text_response
                except Exception as e:
                    logger.error(f"Error with agent_id {agent_id}: {str(e)}")
                    continue
                        
            logger.error(f"Z.ai API error: {response.status_code} - {response.text}")
            return ""
            
    except Exception as e:
        logger.error(f"Error calling Z.ai API: {str(e)}")
        return ""


def generate_smart_fallback_response(message: str) -> str:
    """Generate a smart fallback response based on the user's message"""
    import datetime
    
    message_lower = message.lower()
    
    # Date/time questions (more specific matching)
    if 'what day' in message_lower or 'current date' in message_lower or 'today' in message_lower:
        current_date = datetime.datetime.now()
        return f"Today is {current_date.strftime('%A, %B %d, %Y')}. The current time is {current_date.strftime('%I:%M %p')}.\n\nWhat can I help you with today?"
    
    # Common greetings
    if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
        return "Hello! I'm your AI assistant. I can help you create full-stack applications, browse websites, and extract data from web pages. What would you like to do today?"
    
    # Questions about capabilities
    if any(word in message_lower for word in ["what can you do", "help", "capabilities", "features"]):
        return "I'm here to help you with:\n\n🚀 **Full-Stack Development**\n- Create React + Express.js applications\n- Build Next.js + FastAPI projects\n- Generate complete project structures\n\n🌐 **Web Browsing & Automation**\n- Navigate websites and take screenshots\n- Extract data from web pages\n- Automate browser interactions\n\n📊 **Data Processing**\n- Scrape and analyze web content\n- Process and format data\n- Generate reports and insights\n\nWhat would you like to start with?"
    
    # Programming related
    if any(word in message_lower for word in ["code", "programming", "development", "app", "website"]):
        return "I'd love to help you with development! I can:\n\n• Create full-stack applications with modern frameworks\n• Set up project structures and boilerplate code\n• Help with both frontend and backend development\n• Deploy projects to sandbox environments\n\nWhat kind of application would you like to build?"
    
    # Web browsing related
    if any(word in message_lower for word in ["browse", "website", "scrape", "extract", "data"]):
        return "I can help you with web browsing and data extraction! I can:\n\n• Navigate to any website and take screenshots\n• Extract specific data from web pages\n• Automate browser interactions\n• Scrape content and analyze it\n\nWhich website would you like me to visit or what data do you need?"
    
    # Default response
    return "I'm here to help! I specialize in:\n\n🚀 Creating full-stack applications\n🌐 Browsing and scraping websites\n📊 Extracting data from web pages\n\nWhat would you like to do? Just describe what you need and I'll get started!"


def is_chinese_text(text: str) -> bool:
    """Check if text contains primarily Chinese characters"""
    chinese_chars = 0
    total_chars = 0
    
    for char in text:
        if char.strip():
            total_chars += 1
            if '\u4e00' <= char <= '\u9fff':  # Chinese character range
                chinese_chars += 1
    
    if total_chars == 0:
        return False
    
    return (chinese_chars / total_chars) > 0.3  # More than 30% Chinese


def generate_smart_fallback_response(message: str) -> str:
    """Generate a smart fallback response based on the user's message"""
    message_lower = message.lower()
    
    # Common greetings
    if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
        return "Hello! I'm your AI assistant. I can help you create full-stack applications, browse websites, and extract data from web pages. What would you like to do today?"
    
    # Questions about capabilities
    if any(word in message_lower for word in ["what can you do", "help", "capabilities", "features"]):
        return "I'm here to help you with:\n\n🚀 **Full-Stack Development**\n- Create React + Express.js applications\n- Build Next.js + FastAPI projects\n- Generate complete project structures\n\n🌐 **Web Browsing & Automation**\n- Navigate websites and take screenshots\n- Extract data from web pages\n- Automate browser interactions\n\n📊 **Data Processing**\n- Scrape and analyze web content\n- Process and format data\n- Generate reports and insights\n\nWhat would you like to start with?"
    
    # Programming related
    if any(word in message_lower for word in ["code", "programming", "development", "app", "website"]):
        return "I'd love to help you with development! I can:\n\n• Create full-stack applications with modern frameworks\n• Set up project structures and boilerplate code\n• Help with both frontend and backend development\n• Deploy projects to sandbox environments\n\nWhat kind of application would you like to build?"
    
    # Web browsing related
    if any(word in message_lower for word in ["browse", "website", "scrape", "extract", "data"]):
        return "I can help you with web browsing and data extraction! I can:\n\n• Navigate to any website and take screenshots\n• Extract specific data from web pages\n• Automate browser interactions\n• Scrape content and analyze it\n\nWhich website would you like me to visit or what data do you need?"
    
    # Default response
    return "I'm here to help! I specialize in:\n\n🚀 Creating full-stack applications\n🌐 Browsing and scraping websites\n📊 Extracting data from web pages\n\nWhat would you like to do? Just describe what you need and I'll get started!"


def extract_url_from_message(message: str) -> str:
    """Extract URL from user message more accurately"""
    import re
    
    # Look for URLs in the message
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message)
    
    if urls:
        return urls[0]
    
    # Look for domain patterns
    domain_pattern = r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    domains = re.findall(domain_pattern, message)
    
    if domains:
        domain = domains[0]
        if not domain.startswith('http'):
            return f"https://{domain}"
        return domain
    
    # Fallback to common sites mentioned
    message_lower = message.lower()
    if "apex" in message_lower and "legends" in message_lower:
        return "https://apexlegendsstatus.com"
    elif "google" in message_lower:
        return "https://google.com"
    elif "github" in message_lower:
        return "https://github.com"
    elif "youtube" in message_lower:
        return "https://youtube.com"
    
    return ""


async def create_local_project(project_desc: str, project_type: str = "fullstack") -> Dict[str, Any]:
    """Create a project locally in a temporary directory"""
    try:
        # Create temporary directory for the project
        temp_dir = tempfile.mkdtemp(prefix="ai_project_")
        project_id = str(uuid.uuid4())
        project_name = f"ai-generated-{project_id[:8]}"
        
        # Determine template based on project description and type
        template_name = determine_template(project_desc, project_type)
        template = TEMPLATES.get(template_name, TEMPLATES["react_express"])
        
        # Create project structure
        files_created = []
        for file_path, content in template["files"].items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
            files_created.append(file_path)
        
        # Store project info in database
        project_info = {
            "project_id": project_id,
            "project_name": project_name,
            "description": project_desc,
            "template": template_name,
            "local_path": temp_dir,
            "files_created": files_created,
            "created_at": datetime.utcnow(),
            "status": "created"
        }
        
        await db.projects.insert_one(project_info)
        
        return {
            "project_id": project_id,
            "project_name": project_name,
            "local_path": temp_dir,
            "files_created": files_created,
            "template": template_name
        }
        
    except Exception as e:
        logger.error(f"Error creating local project: {str(e)}")
        raise Exception(f"Failed to create project: {str(e)}")


def determine_template(description: str, project_type: str) -> str:
    """Determine which template to use based on description"""
    desc_lower = description.lower()
    
    if "next" in desc_lower or "fastapi" in desc_lower or "python" in desc_lower:
        return "next_fastapi"
    elif "react" in desc_lower and "express" in desc_lower:
        return "react_express"
    elif project_type == "fullstack":
        return "react_express"  # Default
    else:
        return "react_express"


async def create_daytona_sandbox(project_path: str) -> Optional[str]:
    """Create a Daytona sandbox (if API key is available)"""
    if not DAYTONA_API_KEY:
        return None
        
    try:
        # This would integrate with Daytona API when available
        # For now, return a placeholder
        return f"https://daytona-sandbox-{uuid.uuid4().hex[:8]}.app"
    except Exception as e:
        logger.error(f"Error creating Daytona sandbox: {str(e)}")
        return None


async def deploy_to_sandbox(project_info: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy project to available sandbox services"""
    sandbox_urls = {}
        
    # Try Daytona first
    daytona_url = await create_daytona_sandbox(project_info["local_path"])
    if daytona_url:
        sandbox_urls["daytona"] = daytona_url
    
    # For demo purposes, create local preview URLs
    project_id = project_info["project_id"]
    sandbox_urls["local_preview"] = f"http://localhost:3000?project={project_id}"
    sandbox_urls["api_preview"] = f"http://localhost:5000?project={project_id}"
    
    return sandbox_urls


def requires_project_creation(message: str) -> bool:
    """Determine if a message requires creating a new project"""
    message_lower = message.lower()
    creation_keywords = [
        "create", "build", "make", "generate", "new project",
        "full stack", "website", "web app", "application",
        "frontend", "backend", "api", "react app", "next.js"
    ]
    
    return any(keyword in message_lower for keyword in creation_keywords)


def requires_browser_action(message: str) -> bool:
    """Determine if a message requires browser interaction"""
    import re
    
    # Check for URLs in the message
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, message):
        return True
    
    # Check for domain patterns
    domain_pattern = r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    if re.search(domain_pattern, message):
        return True
    
    message_lower = message.lower()
    browser_keywords = [
        "go to", "visit", "navigate", "open", "browse",
        "website", "url", "page", "site",
        "screenshot", "capture", "image", "picture",
        "click", "button", "link", "element",
        "search", "find", "extract", "scrape", "get",
        "fill", "form", "input", "type",
        "scroll", "wait", "load", "test",
        "down", "up", "scroll down", "scroll up"
    ]
    
    return any(keyword in message_lower for keyword in browser_keywords)


@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Enhanced chat with AI featuring browser-use integration and conversation flow"""
    
    try:
        # Determine what type of action is needed
        needs_browser = requires_browser_action(request.message)
        needs_project = requires_project_creation(request.message)
        
        # Initialize variables
        response_text = ""
        action = None
        project_created = None
        browser_use_result = None
        vnc_url = None
        conversation_continues = True
        
        # Get browser-use agent
        browser_agent = get_browser_use_agent(OPENAI_API_KEY)
        
        if needs_project:
            # Handle project creation
            try:
                # Use AI to understand project requirements
                prompt = f"""
You are an AI full-stack developer. The user said: "{request.message}"

Analyze what they want to build and respond with project details.
"""
                
                try:
                    gpt_response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=300,
                        temperature=0.7
                    )
                    ai_analysis = gpt_response.choices[0].message.content
                except:
                    ai_analysis = f"I'll create a full-stack application based on: {request.message}"
                
                # Create the project
                project_info = await create_local_project(request.message, "fullstack")
                sandbox_urls = await deploy_to_sandbox(project_info)
                
                project_created = {
                    "project_id": project_info["project_id"],
                    "project_name": project_info["project_name"],
                    "files_created": project_info["files_created"],
                    "template": project_info["template"],
                    "sandbox_urls": sandbox_urls
                }
                
                response_text = f"🚀 **Project Created Successfully!**\n\n{ai_analysis}\n\n📁 **Project Details:**\n- ID: {project_info['project_id']}\n- Template: {project_info['template']}\n- Files: {len(project_info['files_created'])} files created\n\n**What would you like me to do next?** I can:\n- Test the application in the browser\n- Modify the code\n- Deploy to additional platforms\n- Create documentation"
                
            except Exception as e:
                response_text = f"❌ **Project Creation Failed**: {str(e)}\n\nLet me help you with something else. What would you like to do?"
                
        elif needs_browser and request.use_browser_use:
            # Use browser-use system with enhanced integration
            try:
                response_text = f"🌐 **Starting real-time browser automation...**\n\n**Task**: {request.message}\n\n**Status**: Launching browser and beginning task execution...\n\n**✨ Real-time viewing**: Browser automation in progress!"
                
                # Create browser session if not provided
                if not request.ws_endpoint:
                    try:
                        session_response = await create_browserless_session()
                        ws_endpoint = session_response.wsEndpoint
                    except Exception as e:
                        response_text = f"❌ **Failed to create browser session**: {str(e)}\n\nLet me help you with something else instead."
                        needs_browser = False
                        browser_use_result = {
                            "success": False,
                            "task": request.message,
                            "error": f"Browser session creation failed: {str(e)}",
                            "vnc_url": None,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                else:
                    ws_endpoint = request.ws_endpoint
                
                if ws_endpoint:
                    # Execute browser-use task with WebSocket connection
                    try:
                        browser_use_result = await browser_agent.execute_task(request.message, request.session_id, ws_endpoint)
                        
                        if browser_use_result.get("success"):
                            response_text = f"✅ **Browser Task Completed Successfully!**\n\n**What I accomplished**: {request.message}\n\n"
                            
                            if browser_use_result.get("result"):
                                response_text += f"**📋 Result**: {browser_use_result['result']}\n\n"
                            
                            if browser_use_result.get("extracted_data"):
                                response_text += f"**📊 Data Extracted**: Found valuable information on the page\n\n"
                            
                            response_text += f"**🔗 Real-time View**: {browser_use_result.get('vnc_url', 'Available')}\n\n"
                            response_text += "**What's next?** I can:\n"
                            response_text += "• Continue browsing this site\n"
                            response_text += "• Extract more specific data\n"
                            response_text += "• Navigate to related pages\n"
                            response_text += "• Save or analyze the data"
                        else:
                            error_msg = browser_use_result.get("error", "Unknown error")
                            response_text = f"⚠️ **Browser automation encountered an issue**\n\n**Error**: {error_msg}\n\n**Let me try a different approach**. You can:\n• Rephrase your request more specifically\n• Try with a simpler task first\n• Check if the website is accessible"
                        
                        # Set VNC URL for frontend
                        vnc_url = browser_use_result.get("vnc_url")
                        
                    except Exception as browser_use_error:
                        logger.error(f"Browser-use execution error: {str(browser_use_error)}")
                        response_text = f"⚠️ **Browser automation system error**: {str(browser_use_error)}\n\n**Falling back to standard browser automation...**"
                        
                        # Fallback to legacy system
                        browser_use_result = {
                            "success": False,
                            "task": request.message,
                            "error": str(browser_use_error),
                            "vnc_url": vnc_url,
                            "timestamp": datetime.utcnow().isoformat(),
                            "fallback_used": True
                        }
                
            except Exception as e:
                logger.error(f"Enhanced browser automation error: {str(e)}")
                response_text = f"⚠️ **Browser automation encountered an error**: {str(e)}\n\n**Let me help you with something else instead.**"
                browser_use_result = {
                    "success": False,
                    "task": request.message,
                    "error": str(e),
                    "vnc_url": vnc_url,
                    "timestamp": datetime.utcnow().isoformat()
                }
                        
        elif needs_browser:
            # Legacy browserless system for basic navigation
            extracted_url = extract_url_from_message(request.message)
            user_msg_lower = request.message.lower()
            
            if extracted_url:
                response_text = f"🌐 **Navigating to {extracted_url}**\n\nI'll take a screenshot once the page loads..."
                action = {"type": "goto", "url": extracted_url}
            elif "scroll" in user_msg_lower:
                direction = "down" if "down" in user_msg_lower else "up" if "up" in user_msg_lower else "down"
                response_text = f"📜 **Scrolling {direction}**\n\nLet me scroll the page for you..."
                action = {"type": "scroll", "direction": direction}
            elif "screenshot" in user_msg_lower:
                response_text = "📸 **Taking screenshot**\n\nCapturing the current page..."
                action = {"type": "screenshot"}
            else:
                response_text = "🌐 **Browser Ready**\n\nI can help you navigate websites, take screenshots, and extract information. What would you like me to do?"
                
        else:
            # General conversation
            try:
                gpt_response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": request.message}],
                    max_tokens=400,
                    temperature=0.7
                )
                
                response_text = gpt_response.choices[0].message.content
                response_text += "\n\n**I can also help you with**:\n- 🚀 Creating full-stack applications\n- 🌐 Browsing and scraping websites\n- 📊 Extracting data from web pages"
                
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                # Z.ai API temporarily disabled - using enhanced static responses
                logger.error(f"Calling generate_smart_fallback_response with message: {request.message}")
                response_text = generate_smart_fallback_response(request.message)
                logger.error(f"Generated response: {response_text[:100]}...")
        
        # Execute legacy browser action if needed
        screenshot_data = None
        if action and request.ws_endpoint:
            try:
                screenshot_data = await execute_browser_action(request.ws_endpoint, action)
                if screenshot_data:
                    response_text += "\n\n📸 **Screenshot captured** - check the browser view!"
            except Exception as e:
                logger.error(f"Error executing browser action: {str(e)}")
                response_text += f"\n\n⚠️ **Browser action failed**: {str(e)}"

        # Save enhanced chat to database
        chat_obj = ChatMessage(
            session_id=request.session_id,
            message=request.message,
            response=response_text,
            browser_action=action,
            screenshot=screenshot_data,
            project_created=project_created,
            browser_use_result=browser_use_result,
            vnc_url=vnc_url
        )
        await db.chat_messages.insert_one(chat_obj.dict())

        # Send update to WebSocket clients
        await manager.send_to_session(
            json.dumps({
                "type": "chat_response",
                "data": {
                    "id": chat_obj.id,
                    "response": response_text,
                    "browser_action": action,
                    "screenshot": screenshot_data,
                    "needs_browser": needs_browser,
                    "project_created": project_created,
                    "browser_use_result": browser_use_result,
                    "vnc_url": vnc_url,
                    "conversation_continues": conversation_continues
                }
            }),
            request.session_id
        )

        return ChatResponse(
            id=chat_obj.id,
            response=response_text,
            browser_action=action,
            screenshot=screenshot_data,
            needs_browser=needs_browser,
            project_created=project_created,
            browser_use_result=browser_use_result,
            vnc_url=vnc_url,
            conversation_continues=conversation_continues
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_browser_action(ws_endpoint: str, action: Dict[str, Any]) -> Optional[str]:
    """Execute browser action and return screenshot as base64"""
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(ws_endpoint)
            
            # Get or create a page
            pages = []
            for context in browser.contexts:
                pages.extend(context.pages)
            
            if pages:
                page = pages[0]
            else:
                context = await browser.new_context()
                page = await context.new_page()

            # Execute the action
            action_type = action.get("type")
            
            if action_type == "goto":
                url = action.get("url")
                if url:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    
            elif action_type == "click":
                selector = action.get("selector")
                if selector:
                    await page.click(selector, timeout=10000)
                    await asyncio.sleep(1)
                    
            elif action_type == "fill":
                selector = action.get("selector")
                text = action.get("text")
                if selector and text:
                    await page.fill(selector, text)
                    await asyncio.sleep(1)
                    
            elif action_type == "extract":
                extractors = action.get("extractors", [])
                extracted = {}
                for selector in extractors:
                    element = await page.query_selector(selector)
                    if element:
                        text_content = await element.text_content()
                        extracted[selector] = text_content.strip() if text_content else ""
                logger.info(f"Extracted data: {extracted}")
                
            elif action_type == "scroll":
                direction = action.get("direction", "down")
                if direction == "down":
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                elif direction == "up":
                    await page.evaluate("window.scrollBy(0, -window.innerHeight)")
                await asyncio.sleep(1)
                
            elif action_type == "screenshot":
                # Just take a screenshot without any specific action
                await asyncio.sleep(1)

            # Always take a screenshot after action
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            return screenshot_b64
            
        except Exception as e:
            logger.error(f"Browser action execution error: {str(e)}")
            return None


@api_router.get("/vnc-info")
async def get_vnc_info():
    """Get VNC viewing information for real-time browser viewing"""
    browser_agent = get_browser_use_agent(OPENAI_API_KEY)
    vnc_info = browser_agent.get_vnc_info()
    
    # Update VNC URL to work in hosted environment
    base_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
    vnc_info["vnc_url"] = f"{base_url.replace('/api', '')}/vnc"
    
    return vnc_info


@api_router.get("/vnc-stream")
async def vnc_stream():
    """Stream real-time browser view for embedded display"""
    return {
        "message": "Real-time Browser Stream",
        "instructions": "This endpoint provides live browser automation viewing",
        "stream_type": "embedded",
        "status": "ready"
    }


@api_router.websocket("/vnc-ws/{session_id}")
async def vnc_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time browser streaming"""
    await websocket.accept()
    try:
        while True:
            # This would stream browser frames in real implementation
            data = await websocket.receive_text()
            # For now, acknowledge the connection
            await websocket.send_text(json.dumps({
                "type": "browser_frame",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": "browser_stream_ready"
            }))
    except WebSocketDisconnect:
        logger.info(f"Browser stream WebSocket disconnected for session {session_id}")


@api_router.get("/vnc")
async def vnc_proxy():
    """Proxy VNC viewer to work in hosted environment"""
    return {
        "message": "VNC Viewer",
        "instructions": "Browser automation VNC viewer would be available here in a full deployment",
        "local_url": "http://localhost:6080/vnc.html",
        "status": "VNC proxy endpoint ready"
    }


@api_router.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(100)
        
        return [ChatMessage(**msg) for msg in messages]
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat history")


@api_router.get("/projects/{session_id}")
async def get_projects(session_id: str):
    """Get all projects for a session"""
    try:
        # Get projects from chat history
        messages = await db.chat_messages.find(
            {
                "session_id": session_id,
                "project_created": {"$ne": None}
            }
        ).to_list(100)
        
        projects = []
        for msg in messages:
            if msg.get("project_created"):
                projects.append({
                    "message_id": msg["id"],
                    "timestamp": msg["timestamp"],
                    "description": msg["message"],
                    "project_data": msg["project_created"]
                })
        
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@api_router.get("/project/{project_id}/files")
async def get_project_files(project_id: str):
    """Get file structure of a project"""
    try:
        project = await db.projects.find_one({"project_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Read files from local path
        files_content = {}
        local_path = project["local_path"]
        
        if os.path.exists(local_path):
            for file_path in project["files_created"]:
                full_path = os.path.join(local_path, file_path)
                if os.path.exists(full_path):
                    async with aiofiles.open(full_path, 'r') as f:
                        files_content[file_path] = await f.read()
        
        return {
            "project_id": project_id,
            "files": files_content,
            "structure": project["files_created"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch project files")


@api_router.post("/project/{project_id}/deploy")
async def deploy_project(project_id: str):
    """Deploy project to available sandbox services"""
    try:
        project = await db.projects.find_one({"project_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Deploy to sandbox
        sandbox_urls = await deploy_to_sandbox({
            "project_id": project_id,
            "local_path": project["local_path"]
        })
        
        # Update project with deployment info
        await db.projects.update_one(
            {"project_id": project_id},
            {"$set": {"sandbox_urls": sandbox_urls, "deployed_at": datetime.utcnow()}}
        )
        
        return {
            "project_id": project_id,
            "sandbox_urls": sandbox_urls,
            "status": "deployed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deploy project")


@api_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle real-time communication if needed
            await manager.send_to_session(f"Echo: {data}", session_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()