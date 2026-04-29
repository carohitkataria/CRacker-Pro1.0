#!/usr/bin/env python3
"""
Backend testing for CRacker Pro - Testing 3 newly added features:
1. POST /api/projects/parse-pdf endpoint
2. Customer PO vs Vendor PO classification in pdf_parser.py
3. Microsoft Graph email notifications (graceful placeholder mode)
"""

import asyncio
import json
import os
import sys
from io import BytesIO
from typing import Dict, Any, Optional

import httpx

# Backend URL from frontend .env
BACKEND_URL = "https://clean-interface-65.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@crackerpro.com"
ADMIN_PASSWORD = "Admin@123"

class TestRunner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.auth_cookies = {}
        self.test_results = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
    async def login_admin(self) -> bool:
        """Login as admin and store auth token/cookies"""
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.auth_cookies = dict(response.cookies)
                self.log_result("Admin login", True, f"Token received: {self.auth_token[:20]}...")
                return True
            else:
                self.log_result("Admin login", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin login", False, f"Exception: {e}")
            return False
            
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
        
    def get_existing_pdf(self) -> Optional[bytes]:
        """Get an existing PDF file from uploads directory"""
        upload_dir = "/app/backend/uploads"
        try:
            for filename in os.listdir(upload_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(upload_dir, filename)
                    with open(filepath, 'rb') as f:
                        return f.read()
        except Exception:
            pass
        return None
        
    def create_test_pdf(self, content_text: str) -> bytes:
        """Create a simple PDF with given text content using pypdfium2"""
        try:
            import pypdfium2 as pdfium
            
            # Create a simple PDF document
            pdf = pdfium.PdfDocument.new()
            page = pdf.new_page(612, 792)  # Letter size
            
            # Add text to the page (basic implementation)
            # Note: pypdfium2 is primarily for reading, so we'll create a minimal PDF
            # For testing purposes, we'll create a very basic PDF structure
            
            # Since pypdfium2 is mainly for reading, let's use a different approach
            # Create a minimal PDF using raw PDF syntax
            pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length {len(content_text) + 50}
>>
stream
BT
/F1 12 Tf
50 750 Td
({content_text.replace(chr(10), ') Tj 0 -15 Td (')}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
{200 + len(content_text)}
%%EOF"""
            
            return pdf_content.encode('utf-8')
            
        except ImportError:
            # Fallback: create a very minimal PDF structure
            content_text_safe = content_text.replace('\n', ' ').replace('(', '').replace(')', '')
            pdf_content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length {len(content_text_safe) + 30}>>stream
BT/F1 12 Tf 50 750 Td({content_text_safe})Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000185 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
{200 + len(content_text_safe)}
%%EOF"""
            return pdf_content.encode('utf-8')
        
    async def test_parse_pdf_endpoint(self):
        """Test 1: POST /api/projects/parse-pdf endpoint"""
        print("\n=== Testing POST /api/projects/parse-pdf ===")
        
        # Test 1a: Endpoint requires auth
        try:
            # Create a fresh client without any auth
            async with httpx.AsyncClient(timeout=30.0) as fresh_client:
                response = await fresh_client.post(f"{BACKEND_URL}/projects/parse-pdf")
                if response.status_code == 422:
                    # FastAPI validates request body before auth, so 422 is expected for missing file
                    # Let's try with a file but no auth
                    files = {"file": ("test.txt", b"test", "text/plain")}
                    response = await fresh_client.post(f"{BACKEND_URL}/projects/parse-pdf", files=files)
                    if response.status_code == 401:
                        self.log_result("parse-pdf requires auth", True, "401 Unauthorized without token")
                    else:
                        self.log_result("parse-pdf requires auth", False, f"Expected 401, got {response.status_code}: {response.text}")
                elif response.status_code == 401:
                    self.log_result("parse-pdf requires auth", True, "401 Unauthorized without token")
                else:
                    self.log_result("parse-pdf requires auth", False, f"Expected 401 or 422, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("parse-pdf requires auth", False, f"Exception: {e}")
            
        # Test 1b: Reject non-PDF files
        try:
            files = {"file": ("test.txt", b"This is not a PDF", "text/plain")}
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            if response.status_code == 400:
                self.log_result("parse-pdf rejects non-PDF", True, "400 for .txt file")
            else:
                self.log_result("parse-pdf rejects non-PDF", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("parse-pdf rejects non-PDF", False, f"Exception: {e}")
            
        # Test 1c: Reject empty file
        try:
            files = {"file": ("empty.pdf", b"", "application/pdf")}
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            if response.status_code == 400:
                self.log_result("parse-pdf rejects empty file", True, "400 for empty PDF")
            else:
                self.log_result("parse-pdf rejects empty file", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("parse-pdf rejects empty file", False, f"Exception: {e}")
            
        # Test 1d: Valid PDF processing
        try:
            # Try to use existing PDF first, fallback to creating one
            pdf_bytes = self.get_existing_pdf()
            if pdf_bytes:
                filename = "existing_po.pdf"
                self.log_result("Using existing PDF", True, f"Found existing PDF, size: {len(pdf_bytes)} bytes")
            else:
                # Create a test PDF with PO content
                pdf_content = """
PURCHASE ORDER

From: DIAL - Delhi International Airport
To: WAISL Digital Solutions Ltd
Vendor: WAISL Digital Solutions Ltd

PO Number: PO-2026-001
PO Date: 15-Jan-2026
Order Value: INR 5,00,000

Description: Smart Gate Management System
Start Date: 01-Feb-2026
End Date: 31-Jul-2026

Milestone 1: Design Phase - 28-Feb-2026 - 1,50,000
Milestone 2: Development - 30-Apr-2026 - 2,00,000
Milestone 3: Deployment - 31-Jul-2026 - 1,50,000
"""
                pdf_bytes = self.create_test_pdf(pdf_content)
                filename = "test_po.pdf"
            
            files = {"file": (filename, pdf_bytes, "application/pdf")}
            
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["file_name", "size", "parsed"]
                if all(field in data for field in required_fields):
                    parsed = data["parsed"]
                    expected_parsed_fields = [
                        "po_type", "po_classification", "customer_po_number", 
                        "po_date", "po_value", "currency", "start_date", "end_date",
                        "billing_type", "description", "vendor_references", 
                        "milestones", "raw_text_excerpt", "warnings",
                        "customer_name", "vendor_name"
                    ]
                    if all(field in parsed for field in expected_parsed_fields):
                        self.log_result("parse-pdf valid PDF", True, 
                                      f"Parsed PO type: {parsed.get('po_type')}, "
                                      f"PO number: {parsed.get('customer_po_number')}, "
                                      f"Milestones: {len(parsed.get('milestones', []))}")
                    else:
                        missing = [f for f in expected_parsed_fields if f not in parsed]
                        self.log_result("parse-pdf valid PDF", False, f"Missing parsed fields: {missing}")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("parse-pdf valid PDF", False, f"Missing response fields: {missing}")
            else:
                self.log_result("parse-pdf valid PDF", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("parse-pdf valid PDF", False, f"Exception: {e}")
            
        # Test 1e: Verify no DB writes (check projects count before/after)
        try:
            # Get projects count before
            response_before = await self.client.get(
                f"{BACKEND_URL}/projects",
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            projects_before = len(response_before.json()) if response_before.status_code == 200 else 0
            
            # Parse another PDF
            pdf_bytes = self.get_existing_pdf() or self.create_test_pdf("Simple PO content for testing")
            files = {"file": ("test2.pdf", pdf_bytes, "application/pdf")}
            
            await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            # Get projects count after
            response_after = await self.client.get(
                f"{BACKEND_URL}/projects",
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            projects_after = len(response_after.json()) if response_after.status_code == 200 else 0
            
            if projects_before == projects_after:
                self.log_result("parse-pdf no DB write", True, f"Projects count unchanged: {projects_before}")
            else:
                self.log_result("parse-pdf no DB write", False, 
                              f"Projects count changed: {projects_before} -> {projects_after}")
                
        except Exception as e:
            self.log_result("parse-pdf no DB write", False, f"Exception: {e}")
            
    async def test_po_classification(self):
        """Test 2: Customer PO vs Vendor PO classification"""
        print("\n=== Testing PO Classification ===")
        
        # Test 2a: Customer PO (WAISL is vendor/recipient)
        try:
            customer_po_content = """
PURCHASE ORDER

From: DIAL - Delhi International Airport
To: WAISL Digital Solutions Ltd
Vendor: WAISL Digital Solutions Ltd
Supplier: WAISL Digital Solutions Ltd

PO Number: CUST-PO-001
Order Value: INR 10,00,000
"""
            pdf_bytes = self.create_test_pdf(customer_po_content)
            files = {"file": ("customer_po.pdf", pdf_bytes, "application/pdf")}
            
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                parsed = data["parsed"]
                po_type = parsed.get("po_type")
                classification = parsed.get("po_classification", {})
                
                if po_type == "Customer PO":
                    self.log_result("Customer PO classification", True, 
                                  f"Correctly identified as Customer PO, confidence: {classification.get('confidence')}")
                else:
                    self.log_result("Customer PO classification", False, 
                                  f"Expected 'Customer PO', got '{po_type}'")
            else:
                self.log_result("Customer PO classification", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Customer PO classification", False, f"Exception: {e}")
            
        # Test 2b: Vendor PO (WAISL is issuer)
        try:
            vendor_po_content = """
WAISL Digital Solutions Ltd
Purchase Order to Supplier

From: WAISL Digital Solutions Ltd
To: NPT Servers Pvt Ltd
Vendor: NPT Servers Pvt Ltd

PO Number: VEND-PO-001
Order Value: INR 5,00,000
"""
            pdf_bytes = self.create_test_pdf(vendor_po_content)
            files = {"file": ("vendor_po.pdf", pdf_bytes, "application/pdf")}
            
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                parsed = data["parsed"]
                po_type = parsed.get("po_type")
                classification = parsed.get("po_classification", {})
                
                if po_type == "Vendor PO":
                    self.log_result("Vendor PO classification", True, 
                                  f"Correctly identified as Vendor PO, confidence: {classification.get('confidence')}")
                else:
                    self.log_result("Vendor PO classification", False, 
                                  f"Expected 'Vendor PO', got '{po_type}'")
            else:
                self.log_result("Vendor PO classification", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Vendor PO classification", False, f"Exception: {e}")
            
        # Test 2c: Unknown PO (no WAISL mention)
        try:
            unknown_po_content = """
PURCHASE ORDER

From: ABC Company Ltd
To: XYZ Suppliers Inc
Vendor: XYZ Suppliers Inc

PO Number: UNKNOWN-001
Order Value: USD 1,000
"""
            pdf_bytes = self.create_test_pdf(unknown_po_content)
            files = {"file": ("unknown_po.pdf", pdf_bytes, "application/pdf")}
            
            response = await self.client.post(
                f"{BACKEND_URL}/projects/parse-pdf",
                files=files,
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                parsed = data["parsed"]
                po_type = parsed.get("po_type")
                classification = parsed.get("po_classification", {})
                confidence = classification.get("confidence")
                
                if po_type == "Unknown" and confidence == "low":
                    self.log_result("Unknown PO classification", True, 
                                  f"Correctly identified as Unknown with low confidence")
                else:
                    self.log_result("Unknown PO classification", False, 
                                  f"Expected 'Unknown' with 'low' confidence, got '{po_type}' with '{confidence}'")
            else:
                self.log_result("Unknown PO classification", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Unknown PO classification", False, f"Exception: {e}")
            
    async def test_notifications(self):
        """Test 3: Microsoft Graph email notifications"""
        print("\n=== Testing Microsoft Graph Notifications ===")
        
        # Test 3a: GET /api/notifications/status (admin required)
        try:
            # Create a fresh client without any auth
            async with httpx.AsyncClient(timeout=30.0) as fresh_client:
                response = await fresh_client.get(f"{BACKEND_URL}/notifications/status")
                if response.status_code == 401:
                    self.log_result("notifications/status requires auth", True, "401 without token")
                else:
                    self.log_result("notifications/status requires auth", False, f"Expected 401, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("notifications/status requires auth", False, f"Exception: {e}")
            
        # Test 3b: GET /api/notifications/status with admin token
        try:
            response = await self.client.get(
                f"{BACKEND_URL}/notifications/status",
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = [
                    "enabled", "configured", "tenant_id_present", 
                    "client_id_present", "client_secret_present", 
                    "sender_email", "default_recipient", "client_id_hint"
                ]
                
                if all(field in data for field in expected_fields):
                    # Check that configured is false (placeholder credentials)
                    if data["configured"] == False:
                        self.log_result("notifications/status response", True, 
                                      f"Configured: {data['configured']}, "
                                      f"Enabled: {data['enabled']}, "
                                      f"Sender: {data['sender_email']}")
                    else:
                        self.log_result("notifications/status response", False, 
                                      "Expected configured=false with placeholder credentials")
                else:
                    missing = [f for f in expected_fields if f not in data]
                    self.log_result("notifications/status response", False, f"Missing fields: {missing}")
            else:
                self.log_result("notifications/status response", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("notifications/status response", False, f"Exception: {e}")
            
        # Test 3c: POST /api/notifications/test (admin, empty body)
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/notifications/test",
                json={},
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("sent") == False and data.get("skipped") == True:
                    reason = data.get("reason", "")
                    if "not configured" in reason.lower() or "placeholder" in reason.lower():
                        self.log_result("notifications/test skipped", True, f"Skipped: {reason}")
                    else:
                        self.log_result("notifications/test skipped", False, f"Unexpected reason: {reason}")
                else:
                    self.log_result("notifications/test skipped", False, 
                                  f"Expected sent=false, skipped=true, got: {data}")
            else:
                self.log_result("notifications/test skipped", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("notifications/test skipped", False, f"Exception: {e}")
            
        # Test 3d: POST /api/notifications/test with custom recipient
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/notifications/test",
                json={"to": "test@example.com"},
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("sent") == False and data.get("skipped") == True:
                    self.log_result("notifications/test custom recipient", True, "Skipped with custom recipient")
                else:
                    self.log_result("notifications/test custom recipient", False, 
                                  f"Expected skipped result, got: {data}")
            else:
                self.log_result("notifications/test custom recipient", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("notifications/test custom recipient", False, f"Exception: {e}")
            
    async def test_existing_flows(self):
        """Test existing flows still work"""
        print("\n=== Testing Existing Flows ===")
        
        # Test existing login flow
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "user" in data and "access_token" in data:
                    self.log_result("Existing login flow", True, "Login successful")
                else:
                    self.log_result("Existing login flow", False, "Missing user or token in response")
            else:
                self.log_result("Existing login flow", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Existing login flow", False, f"Exception: {e}")
            
        # Test projects list
        try:
            response = await self.client.get(
                f"{BACKEND_URL}/projects",
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                projects = response.json()
                self.log_result("Projects list", True, f"Retrieved {len(projects)} projects")
            else:
                self.log_result("Projects list", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Projects list", False, f"Exception: {e}")
            
        # Test project transition (to verify approval email dispatch doesn't crash)
        try:
            # Get first project
            response = await self.client.get(
                f"{BACKEND_URL}/projects",
                headers=self.get_auth_headers(),
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                projects = response.json()
                if projects:
                    project = projects[0]
                    project_id = project["id"]
                    current_stage = project["current_stage"]
                    
                    # Try to transition to next stage (this should trigger approval email dispatch)
                    stage_transitions = {
                        "Pipeline": "Deal P&L",
                        "Deal P&L": "Customer PO",
                        "Customer PO": "Operations",
                        "Operations": "Closure"
                    }
                    
                    target_stage = stage_transitions.get(current_stage)
                    if target_stage:
                        response = await self.client.post(
                            f"{BACKEND_URL}/projects/{project_id}/transition",
                            json={"target_stage": target_stage, "reason": "Test transition"},
                            headers=self.get_auth_headers(),
                            cookies=self.auth_cookies
                        )
                        
                        # Should not crash, regardless of approval requirements
                        if response.status_code in [200, 400]:  # 400 might be approval required
                            self.log_result("Project transition (approval email)", True, 
                                          f"Transition attempt successful, no crash")
                        else:
                            self.log_result("Project transition (approval email)", False, 
                                          f"HTTP {response.status_code}: {response.text}")
                    else:
                        self.log_result("Project transition (approval email)", True, 
                                      f"No valid transition from {current_stage}")
                else:
                    self.log_result("Project transition (approval email)", True, "No projects to test transition")
            else:
                self.log_result("Project transition (approval email)", False, "Could not get projects")
                
        except Exception as e:
            self.log_result("Project transition (approval email)", False, f"Exception: {e}")
            
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting CRacker Pro Backend Tests")
        print(f"Backend URL: {BACKEND_URL}")
        
        # Login first
        if not await self.login_admin():
            print("❌ Cannot proceed without admin login")
            return
            
        # Run all test suites
        await self.test_parse_pdf_endpoint()
        await self.test_po_classification()
        await self.test_notifications()
        await self.test_existing_flows()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}")
            if result["details"] and not result["passed"]:
                print(f"   {result['details']}")
                
        return passed == total


async def main():
    """Main test runner"""
    try:
        async with TestRunner() as runner:
            success = await runner.run_all_tests()
            sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())