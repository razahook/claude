import asyncio
import logging
from typing import Optional, Dict, Any, List
from browser_use import Agent
from browser_use.llm import ChatOpenAI
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
        self.vnc_url = "http://localhost:6080/vnc.html"
        
    async def execute_task(self, task: str, session_id: str) -> Dict[str, Any]:
        """Execute a browser task using browser-use agent"""
        
        try:
            # Initialize the LLM
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=self.openai_api_key,
                temperature=0.7
            )
            
            # Create the agent
            agent = Agent(
                task=task,
                llm=llm,
                # Enable real-time streaming
                save_conversation_path=f"/tmp/browser_use_{session_id}.json",
                # Allow custom browser config
                browser_config={
                    "headless": False,  # Show browser for VNC viewing
                    "args": [
                        "--no-sandbox",
                        "--disable-dev-shm-usage", 
                        "--window-size=1280,720"
                    ]
                }
            )
            
            # Store for potential cancellation
            self.current_agent = agent
            
            # Execute the task
            result = await agent.run()
            
            # Parse the result
            response_data = {
                "success": True,
                "task": task,
                "result": str(result),
                "vnc_url": self.vnc_url,
                "conversation_path": f"/tmp/browser_use_{session_id}.json",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Try to extract structured data if available
            if hasattr(result, 'extracted_data'):
                response_data["extracted_data"] = result.extracted_data
            
            # Add to conversation history
            self.conversation_history.append({
                "task": task,
                "result": response_data,
                "timestamp": datetime.utcnow()
            })
            
            return response_data
            
        except Exception as e:
            logger.error(f"Browser-use agent error: {str(e)}")
            return {
                "success": False,
                "task": task,
                "error": str(e),
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def extract_data(self, task: str, extractors: List[str], session_id: str) -> Dict[str, Any]:
        """Extract specific data from a webpage"""
        
        extraction_task = f"{task}. Extract the following information: {', '.join(extractors)}"
        
        try:
            # Create specialized extraction agent
            llm = ChatOpenAI(
                model="gpt-4o-mini", 
                api_key=self.openai_api_key,
                temperature=0.3  # Lower temperature for data extraction
            )
            
            agent = Agent(
                task=extraction_task,
                llm=llm,
                save_conversation_path=f"/tmp/browser_extract_{session_id}.json",
                browser_config={
                    "headless": False,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage"]
                }
            )
            
            result = await agent.run()
            
            # Parse extracted data
            extracted_data = {}
            
            # Try to parse JSON if the result contains structured data
            result_str = str(result)
            try:
                if '{' in result_str and '}' in result_str:
                    # Extract JSON from the result
                    start = result_str.find('{')
                    end = result_str.rfind('}') + 1
                    json_str = result_str[start:end]
                    extracted_data = json.loads(json_str)
            except:
                # Fallback to simple text extraction
                extracted_data = {"raw_result": result_str}
            
            return {
                "success": True,
                "task": extraction_task,
                "extracted_data": extracted_data,
                "raw_result": result_str,
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data extraction error: {str(e)}")
            return {
                "success": False,
                "task": extraction_task,
                "error": str(e),
                "vnc_url": self.vnc_url,
                "timestamp": datetime.utcnow().isoformat()
            }
    
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
            # Browser-use doesn't have direct cancellation, but we can try
            logger.info("Attempting to cancel current browser-use task")
            self.current_agent = None
    
    def get_vnc_info(self) -> Dict[str, str]:
        """Get VNC viewing information"""
        return {
            "vnc_url": self.vnc_url,
            "vnc_password": "youvncpassword",  # Default password
            "instructions": "Open the VNC URL in your browser to watch the AI interact with websites in real-time"
        }


# Global instance
browser_use_agent = None

def get_browser_use_agent(openai_api_key: str) -> BrowserUseAgent:
    """Get or create browser-use agent instance"""
    global browser_use_agent
    
    if browser_use_agent is None:
        browser_use_agent = BrowserUseAgent(openai_api_key)
    
    return browser_use_agent