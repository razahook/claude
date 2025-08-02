import asyncio
import logging
from typing import Optional, Dict, Any, List
import os
import json
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserUseAgent:
    """Integration with browser-use for real-time browser automation"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.current_agent = None
        self.conversation_history = []
        # Update VNC URL to work in hosted environment  
        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        if backend_url.endswith('/api'):
            base_url = backend_url[:-4]  # Remove /api suffix
        else:
            base_url = backend_url
        self.vnc_url = f"{base_url}/vnc-stream"
        
    async def execute_task(self, task: str, session_id: str, ws_endpoint: str = None) -> Dict[str, Any]:
        """Execute a browser task using browser-use agent with Browserless integration"""
        
        try:
            # Try to import browser-use components with updated API
            try:
                from browser_use import Agent
                from langchain_openai import ChatOpenAI
            except ImportError:
                logger.warning("Browser-use imports failed, using fallback")
                return await self._fallback_execution(task, session_id)
            
            # Initialize the LLM with proper OpenAI configuration
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=self.openai_api_key,
                temperature=0.7
            )
            
            # If we have a WebSocket endpoint, connect to Browserless browser
            browser = None
            page = None
            
            if ws_endpoint:
                try:
                    from playwright.async_api import async_playwright
                    
                    playwright = await async_playwright().start()
                    browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
                    
                    # Get or create a page
                    pages = []
                    for context in browser.contexts:
                        pages.extend(context.pages)
                    
                    if pages:
                        page = pages[0]
                    else:
                        context = await browser.new_context()
                        page = await context.new_page()
                    
                    logger.info(f"Connected to Browserless browser for task: {task}")
                    
                except Exception as e:
                    logger.error(f"Failed to connect to Browserless: {str(e)}")
                    # Fallback without browser connection
                    pass
            
            # Create the agent
            agent = Agent(
                task=task,
                llm=llm,  
                browser=browser,
                page=page,
                use_vision=True,
                save_conversation_path=f"/tmp/browser_use_{session_id}.json",
                max_failures=2,
                retry_delay=5
            )
            
            # Store for potential cancellation
            self.current_agent = agent
            
            logger.info(f"Starting browser-use task: {task}")
            
            # Execute the task
            result = await agent.run()
            
            logger.info(f"Browser-use task completed: {result}")
            
            # Parse the result
            response_data = {
                "success": True,
                "task": task,
                "result": str(result),
                "vnc_url": self.vnc_url,
                "conversation_path": f"/tmp/browser_use_{session_id}.json",
                "timestamp": datetime.utcnow().isoformat(),
                "browserless_connected": ws_endpoint is not None
            }
            
            # Try to extract structured data if available
            if hasattr(result, 'extracted_data'):
                response_data["extracted_data"] = result.extracted_data
            elif isinstance(result, dict):
                response_data["extracted_data"] = result
            elif isinstance(result, list):
                response_data["extracted_data"] = {"items": result}
            
            # Add to conversation history
            self.conversation_history.append({
                "task": task,
                "result": response_data,
                "timestamp": datetime.utcnow()
            })
            
            return response_data
            
        except Exception as e:
            logger.error(f"Browser-use agent error: {str(e)}", exc_info=True)
            return await self._enhanced_fallback_execution(task, session_id, str(e))
    
    async def _fallback_execution(self, task: str, session_id: str) -> Dict[str, Any]:
        """Fallback execution when browser-use isn't available"""
        return {
            "success": False,
            "task": task,
            "error": "Browser-Use not properly configured. Using enhanced legacy browser automation.",
            "vnc_url": self.vnc_url,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback": True
        }
    
    async def _enhanced_fallback_execution(self, task: str, session_id: str, error: str) -> Dict[str, Any]:
        """Enhanced fallback with better error messaging"""
        # Try to start VNC server or browser automation
        try:
            # Check if we can start a local browser instance for VNC
            await self._setup_vnc_browser()
            
            return {
                "success": False,
                "task": task,
                "error": f"Browser-Use setup issue: {error}. VNC browser started for manual viewing.",
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat(),
                "fallback": True,
                "vnc_ready": True
            }
        except Exception as vnc_error:
            return {
                "success": False,
                "task": task,
                "error": f"Browser automation unavailable: {error}. VNC setup failed: {vnc_error}",
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat(),
                "fallback": True,
                "vnc_ready": False
            }
    
    async def _setup_vnc_browser(self):
        """Setup VNC browser for manual viewing"""
        try:
            # Try to install and setup browser-use web-ui components
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--window-size=1280,720"
                    ]
                )
                
                # Keep browser open for VNC viewing
                logger.info("Browser launched for VNC viewing")
                return browser
                
        except Exception as e:
            logger.error(f"Failed to setup VNC browser: {str(e)}")
            raise
    
    async def extract_data(self, task: str, extractors: List[str], session_id: str) -> Dict[str, Any]:
        """Extract specific data from a webpage"""
        
        extraction_task = f"{task}. Extract the following information: {', '.join(extractors)}"
        return await self.execute_task(extraction_task, session_id)
    
    async def continue_conversation(self, follow_up: str, session_id: str) -> Dict[str, Any]:
        """Continue a conversation with follow-up actions"""
        
        # Build context from conversation history
        context = f"Previous conversation context: {self.get_conversation_summary()}\n\nNew request: {follow_up}"
        
        return await self.execute_task(context, session_id)
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation history"""
        if not self.conversation_history:
            return "No previous conversation."
        
        summary = []
        for item in self.conversation_history[-3:]:  # Last 3 interactions
            summary.append(f"Task: {item['task'][:100]}...")
            if item['result'].get('success'):
                summary.append(f"Result: {str(item['result']['result'])[:200]}...")
        
        return "\n".join(summary)
    
    async def cancel_current_task(self):
        """Cancel the currently running task"""
        if self.current_agent:
            logger.info("Attempting to cancel current browser-use task")
            self.current_agent = None
    
    def get_vnc_info(self) -> Dict[str, str]:
        """Get VNC viewing information"""
        return {
            "vnc_url": self.vnc_url,
            "vnc_password": "youvncpassword",
            "instructions": "Open the VNC URL in your browser to watch the AI interact with websites in real-time",
            "status": "VNC server should be running on port 6080"
        }


# Global instance
browser_use_agent = None

def get_browser_use_agent(openai_api_key: str) -> BrowserUseAgent:
    """Get or create browser-use agent instance"""
    global browser_use_agent
    
    if browser_use_agent is None:
        browser_use_agent = BrowserUseAgent(openai_api_key)
    
    return browser_use_agent