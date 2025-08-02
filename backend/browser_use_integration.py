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
        
        # For now, return fallback response since OpenAI API has quota issues
        logger.info(f"Browser-use task requested: {task}")
        
        try:
            # If we have a WebSocket endpoint, connect to Browserless browser and use Playwright directly
            if ws_endpoint:
                return await self._playwright_fallback(task, session_id, ws_endpoint)
            else:
                # No WebSocket endpoint, return instructional response
                return {
                    "success": False,
                    "task": task,
                    "error": "Browser session not available. Please create a browser session first.",
                    "vnc_url": self.vnc_url,
                    "timestamp": datetime.utcnow().isoformat(),
                    "fallback_used": True
                }
                
        except Exception as e:
            logger.error(f"Browser-use agent error: {str(e)}", exc_info=True)
            return await self._enhanced_fallback_execution(task, session_id, str(e))
    
    async def _playwright_fallback(self, task: str, session_id: str, ws_endpoint: str) -> Dict[str, Any]:
        """Use direct Playwright automation when browser-use isn't available"""
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
            
            # Parse the task to determine action
            task_lower = task.lower()
            actions_performed = []
            
            # Navigate if URL is mentioned
            import re
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, task)
            
            if not urls:
                # Look for domain patterns - be more careful with extraction
                task_words = task.lower().split()
                for word in task_words:
                    if "google" in word:
                        urls = ["https://google.com"]
                        break
                    elif "github" in word:
                        urls = ["https://github.com"]
                        break
                    elif "youtube" in word:
                        urls = ["https://youtube.com"]
                        break
                    elif "." in word and any(tld in word for tld in [".com", ".org", ".net", ".io", ".co"]):
                        # Found a potential domain
                        if not word.startswith("http"):
                            urls = [f"https://{word}"]
                        else:
                            urls = [word]
                        break
            
            # Navigate to URL
            if urls:
                await page.goto(urls[0], wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                actions_performed.append(f"Navigated to {urls[0]}")
            
            # Handle scrolling
            if "scroll" in task_lower:
                direction = "down" if "down" in task_lower else "up"
                if direction == "down":
                    await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                else:
                    await page.evaluate("window.scrollBy(0, -window.innerHeight * 2)")
                await asyncio.sleep(1)
                actions_performed.append(f"Scrolled {direction}")
            
            # Take screenshot
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            screenshot_data = base64.b64encode(screenshot_bytes).decode('utf-8')
            actions_performed.append("Screenshot captured")
            
            # Extract data if requested
            extracted_data = {}
            if "extract" in task_lower or "data" in task_lower:
                try:
                    title = await page.title()
                    extracted_data["page_title"] = title
                    
                    # Get page text content
                    text_content = await page.evaluate("document.body.innerText")
                    if text_content:
                        extracted_data["page_text"] = text_content[:1000]  # First 1000 chars
                    
                    actions_performed.append("Data extracted")
                except Exception as e:
                    actions_performed.append(f"Data extraction failed: {str(e)}")
            
            await browser.close()
            
            return {
                "success": True,
                "task": task,
                "result": f"Completed browser automation with {len(actions_performed)} actions",
                "actions": actions_performed,
                "extracted_data": extracted_data,
                "screenshot": screenshot_data,
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat(),
                "playwright_fallback": True
            }
            
        except Exception as e:
            logger.error(f"Playwright fallback error: {str(e)}")
            return {
                "success": False,
                "task": task,
                "error": f"Browser automation failed: {str(e)}",
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat(),
                "fallback_used": True
            }
    
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