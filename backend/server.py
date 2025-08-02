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

class ChatRequest(BaseModel):
    session_id: str
    message: str
    ws_endpoint: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    response: str
    browser_action: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    needs_browser: Optional[bool] = False
    project_created: Optional[Dict[str, Any]] = None

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
    """Call Z.ai API as an alternative to OpenAI"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.z.ai/api/v1/agents",
                headers={
                    "Authorization": f"Bearer {ZAI_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept-Language": "en-US,en"
                },
                json={
                    "agent_id": "general_translation",  # Using general translation as it might work for general chat
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
                        
            logger.error(f"Z.ai API error: {response.status_code} - {response.text}")
            return ""
            
    except Exception as e:
        logger.error(f"Error calling Z.ai API: {str(e)}")
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
    message_lower = message.lower()
    browser_keywords = [
        "go to", "visit", "navigate", "open", "browse",
        "website", "url", "page", "site",
        "screenshot", "capture", "image", "picture",
        "click", "button", "link", "element",
        "search", "find", "extract", "scrape", "get",
        "fill", "form", "input", "type",
        "scroll", "wait", "load", "test"
    ]
    
    return any(keyword in message_lower for keyword in browser_keywords)


@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with AI and execute browser actions"""
    
    try:
        # Determine if browser action is needed
        needs_browser = requires_browser_action(request.message)
        
        # Create AI prompt for conversational browsing
        if needs_browser:
            prompt = f"""
You are an AI assistant that can control a web browser to help users. The user said: "{request.message}"

Analyze the user's request and respond in a conversational way. If they want you to:
1. Visit a website - create a "goto" action
2. Extract information - create an "extract" action  
3. Click something - create a "click" action
4. Fill a form - create a "fill" action
5. Take a screenshot - create a "screenshot" action

Respond with JSON in this format:
{{
    "response": "Your conversational response to the user",
    "action": {{
        "type": "goto|extract|click|fill|screenshot",
        "url": "URL if goto action",
        "selector": "CSS selector if click/fill action",
        "text": "Text to fill if fill action",
        "extractors": ["selector1", "selector2"] // if extract action
    }},
    "needs_browser": true
}}

If no browser action is needed, just include the response field without action.
"""
        else:
            prompt = f"""
You are a helpful AI assistant. The user said: "{request.message}"

Respond conversationally and helpfully. This request does not require web browsing.

Respond with JSON in this format:
{{
    "response": "Your helpful conversational response to the user",
    "action": null,
    "needs_browser": false
}}
"""

        # Try OpenAI first, then Z.ai, then fallback
        ai_output = ""
        
        try:
            gpt_response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            ai_output = gpt_response.choices[0].message.content
            if not ai_output:
                raise Exception("No AI response received")
                
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            
            # Try Z.ai API
            if needs_browser:
                zai_prompt = f"I need help with web browsing: {request.message}. Please provide step-by-step instructions."
            else:
                zai_prompt = request.message
                
            zai_response = await call_zai_api(zai_prompt)
            
            if zai_response:
                # Convert Z.ai response to our format
                if needs_browser:
                    user_msg_lower = request.message.lower()
                    
                    if "google" in user_msg_lower or "go to" in user_msg_lower:
                        url = "https://google.com"
                        if "github" in user_msg_lower:
                            url = "https://github.com"
                        elif "example" in user_msg_lower:
                            url = "https://example.com"
                        elif "youtube" in user_msg_lower:
                            url = "https://youtube.com"
                            
                        ai_output = f'''{{
    "response": "{zai_response} I'll navigate to {url} for you.",
    "action": {{
        "type": "goto",
        "url": "{url}"
    }},
    "needs_browser": true
}}'''
                    elif "screenshot" in user_msg_lower:
                        ai_output = f'''{{
    "response": "{zai_response} I'll take a screenshot for you.",
    "action": {{
        "type": "screenshot"
    }},
    "needs_browser": true
}}'''
                    else:
                        ai_output = f'''{{
    "response": "{zai_response}",
    "action": null,
    "needs_browser": true
}}'''
                else:
                    ai_output = f'''{{
    "response": "{zai_response}",
    "action": null,
    "needs_browser": false
}}'''
            else:
                # Enhanced fallback response based on user input
                user_msg_lower = request.message.lower()
                
                if needs_browser:
                    if "google" in user_msg_lower or "go to" in user_msg_lower:
                        url = "https://google.com"
                        if "github" in user_msg_lower:
                            url = "https://github.com"
                        elif "example" in user_msg_lower:
                            url = "https://example.com"
                        elif "youtube" in user_msg_lower:
                            url = "https://youtube.com"
                            
                        ai_output = f'''{{
    "response": "I'll navigate to {url} for you. Please wait while I load the page...",
    "action": {{
        "type": "goto",
        "url": "{url}"
    }},
    "needs_browser": true
}}'''
                    elif "screenshot" in user_msg_lower or "take a" in user_msg_lower:
                        ai_output = '''{{
    "response": "I'll take a screenshot of the current page for you.",
    "action": {{
        "type": "screenshot"
    }},
    "needs_browser": true
}}'''
                    elif "click" in user_msg_lower:
                        ai_output = '''{{
    "response": "I understand you want me to click something. Could you be more specific about what element to click?",
    "action": null,
    "needs_browser": true
}}'''
                    elif "extract" in user_msg_lower or "get" in user_msg_lower:
                        ai_output = '''{{
    "response": "I'll extract information from the current page for you.",
    "action": {{
        "type": "extract",
        "extractors": ["title", "h1", "p"]
    }},
    "needs_browser": true
}}'''
                    else:
                        ai_output = f'''{{
    "response": "I can help you browse the web! I can navigate to websites, take screenshots, click elements, and extract information. What would you like me to do?",
    "action": null,
    "needs_browser": true
}}'''
                else:
                    ai_output = f'''{{
    "response": "I'm here to help! I can assist with web browsing tasks like navigating to websites, taking screenshots, and extracting information. What would you like to know or do?",
    "action": null,
    "needs_browser": false
}}'''

        # Parse AI JSON output
        try:
            parsed = json.loads(ai_output)
            response_text = parsed.get("response", "I'm processing your request...")
            action = parsed.get("action")
            needs_browser_response = parsed.get("needs_browser", needs_browser)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {ai_output}")
            response_text = "I understand you want me to help. Could you be more specific?"
            action = None
            needs_browser_response = False

        # Execute browser action if provided and we have a WebSocket endpoint
        screenshot_data = None
        if action and request.ws_endpoint and needs_browser_response:
            try:
                screenshot_data = await execute_browser_action(request.ws_endpoint, action)
            except Exception as e:
                logger.error(f"Error executing browser action: {str(e)}")
                response_text += f" (Note: Browser action failed: {str(e)})"

        # Save chat to database
        chat_obj = ChatMessage(
            session_id=request.session_id,
            message=request.message,
            response=response_text,
            browser_action=action,
            screenshot=screenshot_data
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
                    "needs_browser": needs_browser_response
                }
            }),
            request.session_id
        )

        return ChatResponse(
            id=chat_obj.id,
            response=response_text,
            browser_action=action,
            screenshot=screenshot_data,
            needs_browser=needs_browser_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
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