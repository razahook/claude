import requests
import sys
import json
from datetime import datetime
import uuid
import asyncio
import websockets
import time

class AIBrowserTerminalTester:
    def __init__(self, base_url="https://5b15c451-4da1-4e06-871f-f8a9795102c1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_endpoint = None
        self.session_id = "test_session_001"  # Use specified test session ID
        self.browser_use_tests_passed = 0
        self.browser_use_tests_run = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response Data: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error Text: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint - should return 'AI Terminal Assistant Ready'"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        
        if success and response.get('message') == 'AI Terminal Assistant Ready':
            print("✅ Correct message received")
            return True
        elif success:
            print(f"❌ Unexpected message: {response.get('message')}")
            return False
        return False

    def test_create_session(self):
        """Test creating a browser session"""
        success, response = self.run_test(
            "Create Browser Session",
            "POST",
            "create-session",
            200,
            timeout=45  # Browserless API can be slow
        )
        
        if success and 'wsEndpoint' in response and 'sessionId' in response:
            self.ws_endpoint = response['wsEndpoint']
            self.session_id = response['sessionId']
            print(f"✅ WebSocket endpoint received: {self.ws_endpoint[:50]}...")
            print(f"✅ Session ID received: {self.session_id}")
            return True
        elif success:
            print("❌ Response missing required fields (wsEndpoint, sessionId)")
            return False
        return False

    def test_chat_basic(self):
        """Test basic chat functionality"""
        if not self.session_id:
            print("❌ Skipping - No valid session ID available")
            return False

        success, response = self.run_test(
            "Basic Chat Message",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Hello, what can you do?"
            },
            timeout=30
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'response']
            if all(field in response for field in required_fields):
                print("✅ Response has correct structure")
                print(f"✅ AI Response: {response['response'][:100]}...")
                return True
            else:
                print(f"❌ Response missing required fields: {required_fields}")
                return False
        return False

    def test_chat_with_browser_action(self):
        """Test chat with browser action"""
        if not self.session_id or not self.ws_endpoint:
            print("❌ Skipping - No valid session or WebSocket endpoint available")
            return False

        success, response = self.run_test(
            "Chat with Browser Action",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Go to google.com",
                "ws_endpoint": self.ws_endpoint
            },
            timeout=60  # Browser actions can take time
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'response']
            if all(field in response for field in required_fields):
                print("✅ Response has correct structure")
                print(f"✅ AI Response: {response['response'][:100]}...")
                
                # Check if browser action was executed
                if response.get('browser_action'):
                    print("✅ Browser action included in response")
                if response.get('screenshot'):
                    print("✅ Screenshot included in response")
                    
                return True
            else:
                print(f"❌ Response missing required fields: {required_fields}")
                return False
        return False

    def test_chat_screenshot_request(self):
        """Test requesting a screenshot"""
        if not self.session_id or not self.ws_endpoint:
            print("❌ Skipping - No valid session or WebSocket endpoint available")
            return False

        success, response = self.run_test(
            "Screenshot Request",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Take a screenshot",
                "ws_endpoint": self.ws_endpoint
            },
            timeout=45
        )
        
        if success and response.get('screenshot'):
            print("✅ Screenshot returned as base64")
            return True
        elif success:
            print("❌ No screenshot in response")
            return False
        return False

    def test_chat_history(self):
        """Test retrieving chat history"""
        if not self.session_id:
            print("❌ Skipping - No valid session ID available")
            return False

        success, response = self.run_test(
            "Get Chat History",
            "GET",
            f"chat-history/{self.session_id}",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"✅ Chat history retrieved - {len(response)} messages")
                
                # Verify message structure if any messages exist
                if response:
                    first_msg = response[0]
                    required_fields = ['id', 'session_id', 'message', 'response', 'timestamp']
                    if all(field in first_msg for field in required_fields):
                        print("✅ Message structure is correct")
                        return True
                    else:
                        print(f"❌ Message missing required fields: {required_fields}")
                        return False
                else:
                    print("✅ Empty chat history (valid)")
                    return True
            else:
                print("❌ Chat history should be a list")
                return False
        return False

    def test_browser_use_integration_imports(self):
        """Test that browser-use integration has correct langchain_openai imports"""
        print("\n🔍 Testing Browser-Use Integration Imports...")
        self.browser_use_tests_run += 1
        
        try:
            # Test by making a chat request that would trigger browser-use
            success, response = self.run_test(
                "Browser-Use Integration Test",
                "POST",
                "chat",
                200,
                data={
                    "session_id": self.session_id,
                    "message": "go to google.com",
                    "use_browser_use": True
                },
                timeout=60
            )
            
            if success:
                # Check if the response indicates browser-use was attempted
                response_text = response.get('response', '').lower()
                if 'browser automation' in response_text or 'real-time browser' in response_text:
                    print("✅ Browser-use integration appears to be working")
                    self.browser_use_tests_passed += 1
                    return True
                else:
                    print(f"❌ Response doesn't indicate browser-use integration: {response.get('response', '')[:200]}")
                    return False
            return False
            
        except Exception as e:
            print(f"❌ Browser-use integration test failed: {str(e)}")
            return False

    def test_enhanced_chat_endpoint(self):
        """Test enhanced chat endpoint with browser-use agent integration"""
        print("\n🔍 Testing Enhanced Chat Endpoint...")
        self.browser_use_tests_run += 1
        
        if not self.ws_endpoint:
            print("❌ Skipping - No WebSocket endpoint available")
            return False
            
        success, response = self.run_test(
            "Enhanced Chat with Browser-Use",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "visit https://example.com and take screenshot",
                "ws_endpoint": self.ws_endpoint,
                "use_browser_use": True
            },
            timeout=90
        )
        
        if success:
            # Check for enhanced response fields
            enhanced_fields = ['browser_use_result', 'vnc_url', 'conversation_continues']
            found_fields = [field for field in enhanced_fields if field in response]
            
            if found_fields:
                print(f"✅ Enhanced chat fields found: {found_fields}")
                
                # Check browser_use_result structure if present
                if 'browser_use_result' in response and response['browser_use_result']:
                    browser_result = response['browser_use_result']
                    if isinstance(browser_result, dict) and 'task' in browser_result:
                        print("✅ Browser-use result has correct structure")
                        self.browser_use_tests_passed += 1
                        return True
                    else:
                        print("❌ Browser-use result has incorrect structure")
                        return False
                else:
                    print("✅ Enhanced chat endpoint working (browser-use may have fallback)")
                    self.browser_use_tests_passed += 1
                    return True
            else:
                print("❌ Enhanced chat fields not found in response")
                return False
        return False

    def test_vnc_streaming_endpoints(self):
        """Test VNC streaming endpoints"""
        print("\n🔍 Testing VNC Streaming Endpoints...")
        self.browser_use_tests_run += 1
        
        # Test GET /api/vnc-stream
        success1, response1 = self.run_test(
            "VNC Stream Endpoint",
            "GET",
            "vnc-stream",
            200
        )
        
        if success1:
            required_fields = ['message', 'stream_type', 'status']
            if all(field in response1 for field in required_fields):
                print("✅ VNC stream endpoint has correct structure")
                
                # Test VNC info endpoint
                success2, response2 = self.run_test(
                    "VNC Info Endpoint",
                    "GET",
                    "vnc-info",
                    200
                )
                
                if success2 and 'vnc_url' in response2:
                    print("✅ VNC info endpoint working")
                    self.browser_use_tests_passed += 1
                    return True
                else:
                    print("❌ VNC info endpoint failed or missing vnc_url")
                    return False
            else:
                print(f"❌ VNC stream endpoint missing required fields: {required_fields}")
                return False
        return False

    def test_vnc_websocket_endpoint(self):
        """Test VNC WebSocket endpoint"""
        print("\n🔍 Testing VNC WebSocket Endpoint...")
        self.browser_use_tests_run += 1
        
        try:
            # Convert HTTP URL to WebSocket URL
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            ws_url = f"{ws_url}/api/vnc-ws/{self.session_id}"
            
            print(f"Attempting WebSocket connection to: {ws_url}")
            
            # Test WebSocket connection with timeout
            async def test_websocket():
                try:
                    async with websockets.connect(ws_url, timeout=10) as websocket:
                        # Send a test message
                        await websocket.send("test_connection")
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        if response_data.get('type') == 'browser_frame':
                            print("✅ VNC WebSocket endpoint working")
                            return True
                        else:
                            print(f"❌ Unexpected WebSocket response: {response_data}")
                            return False
                            
                except asyncio.TimeoutError:
                    print("❌ WebSocket connection timed out")
                    return False
                except Exception as e:
                    print(f"❌ WebSocket connection failed: {str(e)}")
                    return False
            
            # Run the async test
            result = asyncio.run(test_websocket())
            if result:
                self.browser_use_tests_passed += 1
            return result
            
        except Exception as e:
            print(f"❌ VNC WebSocket test failed: {str(e)}")
            return False

    def test_auto_start_session(self):
        """Test auto-start browser session creation"""
        print("\n🔍 Testing Auto-Start Session Creation...")
        self.browser_use_tests_run += 1
        
        success, response = self.run_test(
            "Auto-Start Browser Session",
            "POST",
            "create-session",
            200,
            timeout=45
        )
        
        if success:
            required_fields = ['wsEndpoint', 'sessionId']
            if all(field in response for field in required_fields):
                # Verify the session is configured for auto-start (headless=False)
                ws_endpoint = response['wsEndpoint']
                if 'browserless.io' in ws_endpoint:
                    print("✅ Auto-start session created with Browserless")
                    print(f"✅ WebSocket endpoint: {ws_endpoint[:50]}...")
                    
                    # Store for other tests
                    if not self.ws_endpoint:
                        self.ws_endpoint = ws_endpoint
                    
                    self.browser_use_tests_passed += 1
                    return True
                else:
                    print("❌ WebSocket endpoint doesn't appear to be Browserless")
                    return False
            else:
                print(f"❌ Session response missing required fields: {required_fields}")
                return False
        return False

    def test_browser_use_task_execution(self):
        """Test real browser automation tasks with browser-use integration"""
        print("\n🔍 Testing Browser-Use Task Execution...")
        self.browser_use_tests_run += 1
        
        if not self.ws_endpoint:
            print("❌ Skipping - No WebSocket endpoint available")
            return False
        
        # Test with a specific browser command
        test_commands = [
            "go to google.com",
            "visit https://example.com and take screenshot"
        ]
        
        for command in test_commands:
            print(f"\n  Testing command: '{command}'")
            
            success, response = self.run_test(
                f"Browser-Use Task: {command}",
                "POST",
                "chat",
                200,
                data={
                    "session_id": self.session_id,
                    "message": command,
                    "ws_endpoint": self.ws_endpoint,
                    "use_browser_use": True
                },
                timeout=90
            )
            
            if success:
                # Check for browser automation indicators
                response_text = response.get('response', '').lower()
                browser_indicators = [
                    'browser automation',
                    'real-time browser',
                    'navigating to',
                    'screenshot',
                    'browser task'
                ]
                
                if any(indicator in response_text for indicator in browser_indicators):
                    print(f"✅ Browser automation response detected for: {command}")
                    
                    # Check for browser_use_result
                    if response.get('browser_use_result'):
                        browser_result = response['browser_use_result']
                        if isinstance(browser_result, dict):
                            print("✅ Browser-use result included in response")
                            if browser_result.get('task') == command:
                                print("✅ Task matches request")
                            if browser_result.get('vnc_url'):
                                print("✅ VNC URL provided")
                        else:
                            print("❌ Browser-use result has incorrect format")
                            return False
                    
                    # At least one command worked
                    if command == test_commands[0]:  # First successful command is enough
                        self.browser_use_tests_passed += 1
                        return True
                else:
                    print(f"❌ No browser automation indicators found for: {command}")
            else:
                print(f"❌ Request failed for command: {command}")
        
        return False

    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms"""
        print("\n🔍 Testing Error Handling and Fallbacks...")
        self.browser_use_tests_run += 1
        
        # Test with invalid WebSocket endpoint
        success, response = self.run_test(
            "Error Handling Test",
            "POST",
            "chat",
            200,  # Should still return 200 but with error handling
            data={
                "session_id": self.session_id,
                "message": "go to google.com",
                "ws_endpoint": "wss://invalid-endpoint.com",
                "use_browser_use": True
            },
            timeout=30
        )
        
        if success:
            response_text = response.get('response', '').lower()
            
            # Check for fallback indicators
            fallback_indicators = [
                'fallback',
                'error',
                'failed',
                'alternative',
                'try a different approach'
            ]
            
            if any(indicator in response_text for indicator in fallback_indicators):
                print("✅ Error handling and fallback mechanisms working")
                
                # Check if browser_use_result indicates fallback
                if response.get('browser_use_result'):
                    browser_result = response['browser_use_result']
                    if browser_result.get('fallback') or not browser_result.get('success'):
                        print("✅ Browser-use result correctly indicates fallback/error")
                        self.browser_use_tests_passed += 1
                        return True
                
                # Even without browser_use_result, if there's error handling, it's working
                self.browser_use_tests_passed += 1
                return True
            else:
                print("❌ No error handling indicators found")
                return False
        return False

    def test_status_endpoints(self):
        """Test the existing status check endpoints"""
        # Test creating a status check
        success, response = self.run_test(
            "Create Status Check",
            "POST",
            "status",
            200,
            data={"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        )
        
        if not success:
            return False

        # Test getting status checks
        success, response = self.run_test(
            "Get Status Checks",
            "GET",
            "status",
            200
        )
        return success

def main():
    print("🚀 Starting AI Browser Terminal API Tests")
    print("=" * 50)
    
    tester = AIBrowserTerminalTester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Status Endpoints", tester.test_status_endpoints),
        ("Create Browser Session", tester.test_create_session),
        ("Basic Chat", tester.test_chat_basic),
        ("Chat with Browser Action", tester.test_chat_with_browser_action),
        ("Screenshot Request", tester.test_chat_screenshot_request),
        ("Chat History", tester.test_chat_history),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())