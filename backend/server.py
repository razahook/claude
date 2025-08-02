from fastapi import FastAPI, APIRouter, HTTPException
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


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
BROWSERLESS_API_KEY = os.environ['BROWSERLESS_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class BrowserSessionResponse(BaseModel):
    wsEndpoint: str

class RunTaskRequest(BaseModel):
    wsEndpoint: str
    targetUrl: str

class RunTaskResponse(BaseModel):
    extracted: Dict[str, Any]
    aiOutput: str


# Existing routes
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

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


# New agentic scraper routes
@api_router.post("/create-session", response_model=BrowserSessionResponse)
async def create_browserless_session():
    """Create a new Browserless session and return wsEndpoint"""
    try:
        session_config = {
            "ttl": 300000,  # 5 minutes
            "stealth": True,
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling"
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
            # The response contains 'connect' field with the WebSocket endpoint
            return BrowserSessionResponse(wsEndpoint=data["connect"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Browserless session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create browser session")


@api_router.post("/run-task", response_model=RunTaskResponse)
async def run_agentic_task(request: RunTaskRequest):
    """Run AI-controlled browsing and scraping task"""
    
    if not request.wsEndpoint or not request.targetUrl:
        raise HTTPException(status_code=400, detail="Missing wsEndpoint or targetUrl")
    
    try:
        # Create the AI prompt
        prompt = f"""
You are an AI agent controlling a browser.
Navigate to this URL: {request.targetUrl}
Extract the page title and first paragraph text.
Respond with JSON:
{{
    "actions": [
        {{"type": "goto", "url": "{request.targetUrl}"}},
        {{"type": "extract", "selectors": ["title", "p"]}}
    ]
}}
"""

        # Call OpenAI GPT API
        try:
            gpt_response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            
            ai_output = gpt_response.choices[0].message.content
            if not ai_output:
                raise HTTPException(status_code=500, detail="No AI response received")
                
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

        # Parse AI JSON output
        try:
            parsed = json.loads(ai_output)
            actions = parsed.get("actions", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {ai_output}")
            raise HTTPException(status_code=500, detail="Failed to parse AI response")

        # Execute actions using Playwright connected to Browserless
        extracted = {}
        
        async with async_playwright() as p:
            try:
                # Connect to the Browserless session
                browser = await p.chromium.connect_over_cdp(request.wsEndpoint)
                
                # Get the existing page or create new one
                pages = browser.contexts[0].pages if browser.contexts and browser.contexts[0].pages else []
                if pages:
                    page = pages[0]
                else:
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    page = await context.new_page()

                # Execute the AI-generated actions
                for action in actions:
                    if action.get("type") == "goto":
                        await page.goto(action.get("url"), wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(2)  # Wait for page to stabilize
                        
                    elif action.get("type") == "extract":
                        selectors = action.get("selectors", [])
                        for selector in selectors:
                            try:
                                if selector == "title":
                                    extracted[selector] = await page.title()
                                elif selector == "p":
                                    # Get first paragraph text
                                    first_p = await page.query_selector("p")
                                    if first_p:
                                        extracted[selector] = await first_p.text_content()
                                    else:
                                        extracted[selector] = ""
                                else:
                                    # Generic selector extraction
                                    element = await page.query_selector(selector)
                                    if element:
                                        extracted[selector] = await element.text_content()
                                    else:
                                        extracted[selector] = ""
                            except Exception as e:
                                logger.error(f"Error extracting {selector}: {str(e)}")
                                extracted[selector] = f"Error: {str(e)}"

                await browser.close()
                
            except Exception as e:
                logger.error(f"Playwright execution error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Browser execution error: {str(e)}")

        return RunTaskResponse(extracted=extracted, aiOutput=ai_output)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running AI task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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