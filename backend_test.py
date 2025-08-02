import requests
import sys
import json
from datetime import datetime

class AgenticScraperAPITester:
    def __init__(self, base_url="https://b18f6d36-d162-472e-8488-24248bb6fe54.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_endpoint = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
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
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_create_session(self):
        """Test creating a Browserless session"""
        success, response = self.run_test(
            "Create Browser Session",
            "POST",
            "create-session",
            200,
            timeout=45  # Browserless API can be slow
        )
        
        if success and 'wsEndpoint' in response:
            self.ws_endpoint = response['wsEndpoint']
            print(f"✅ WebSocket endpoint received: {self.ws_endpoint[:50]}...")
            return True
        elif success:
            print("❌ Response missing 'wsEndpoint' field")
            return False
        return False

    def test_run_task_without_session(self):
        """Test running task without valid session (should fail)"""
        success, response = self.run_test(
            "Run Task Without Session",
            "POST",
            "run-task",
            400,  # Should return 400 for missing wsEndpoint
            data={
                "wsEndpoint": "",
                "targetUrl": "https://example.com"
            }
        )
        return success

    def test_run_task_without_url(self):
        """Test running task without URL (should fail)"""
        success, response = self.run_test(
            "Run Task Without URL",
            "POST",
            "run-task",
            400,  # Should return 400 for missing targetUrl
            data={
                "wsEndpoint": "ws://fake-endpoint",
                "targetUrl": ""
            }
        )
        return success

    def test_run_task_with_valid_data(self):
        """Test running task with valid session and URL"""
        if not self.ws_endpoint:
            print("❌ Skipping - No valid WebSocket endpoint available")
            return False

        success, response = self.run_test(
            "Run AI Scraping Task",
            "POST",
            "run-task",
            200,
            data={
                "wsEndpoint": self.ws_endpoint,
                "targetUrl": "https://example.com"
            },
            timeout=60  # AI + browser automation can take time
        )
        
        if success:
            # Verify response structure
            if 'extracted' in response and 'aiOutput' in response:
                print("✅ Response has correct structure (extracted, aiOutput)")
                
                extracted = response.get('extracted', {})
                if 'title' in extracted:
                    print(f"✅ Page title extracted: {extracted['title']}")
                if 'p' in extracted:
                    print(f"✅ First paragraph extracted: {extracted['p'][:100]}...")
                
                return True
            else:
                print("❌ Response missing required fields (extracted, aiOutput)")
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
    print("🚀 Starting Agentic Scraper API Tests")
    print("=" * 50)
    
    tester = AgenticScraperAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Status Endpoints", tester.test_status_endpoints),
        ("Create Browser Session", tester.test_create_session),
        ("Run Task - No Session", tester.test_run_task_without_session),
        ("Run Task - No URL", tester.test_run_task_without_url),
        ("Run Task - Valid Data", tester.test_run_task_with_valid_data),
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