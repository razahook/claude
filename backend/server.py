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

class BrowserSessionResponse(BaseModel):
    wsEndpoint: str
    sessionId: str

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


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
        "scroll", "wait", "load"
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