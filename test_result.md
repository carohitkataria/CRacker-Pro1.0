#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Continuation:
  1. Add PDF parsing at the time of New Project creation so the user doesn't need to
     fill all details manually. Confirm before applying. Detect Customer PO vs Vendor PO
     (Customer PO: WAISL is the vendor; Vendor PO: WAISL is the issuer).
  2. Add a new theme color: #5C2B84, #FFC000 and white. Make pie/bar charts more
     colorful and minimalistic.
  3. Configure secure email notification for Microsoft suite. Recipient:
     rohit.kataria@waisldigital.com. Use Azure AD / MS Graph (placeholder credentials
     for now — user will provide real ones later).

backend:
  - task: "POST /api/projects/parse-pdf preview endpoint (no DB write)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -agent: "main"
        -comment: "Added new endpoint that runs pdf_parser on uploaded PDF and returns
         extracted fields without storing the file. Used by ProjectFormModal."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED: All functionality working correctly. Endpoint requires auth (401 without token), rejects non-PDF files (400), rejects empty files (400), successfully parses valid PDFs with all expected fields (po_type, po_classification, customer_po_number, po_date, po_value, currency, start_date, end_date, billing_type, description, vendor_references, milestones, raw_text_excerpt, warnings, customer_name, vendor_name), and confirmed NO database writes occur during parsing."

  - task: "Customer PO vs Vendor PO classification in pdf_parser"
    implemented: true
    working: true
    file: "backend/pdf_parser.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -agent: "main"
        -comment: "Rewrote parser. Adds po_classification (po_type, issuer, recipient,
         confidence) using WAISL aliases. Customer PO → WAISL is recipient.
         Vendor PO → WAISL is issuer/header. Existing milestone/PO-number/value
         extraction preserved and improved."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED: Classification logic working perfectly. Customer PO correctly identified when WAISL is vendor/recipient (confidence: medium), Vendor PO correctly identified when WAISL is issuer (confidence: medium), Unknown PO correctly identified when no WAISL mention (confidence: low). All test cases passed with expected po_type and confidence levels."

  - task: "Microsoft Graph email notifications (graceful when creds are placeholders)"
    implemented: true
    working: true
    file: "backend/notifications.py, backend/server.py, backend/.env"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -agent: "main"
        -comment: "Added GraphMailer (httpx-based, OAuth2 client credentials, in-memory
         token cache with asyncio lock). Added /api/notifications/status (admin) and
         /api/notifications/test (admin). Hooked transition→approval-request flow to
         dispatch an approval email asynchronously. With placeholder env values
         (REPLACE_*) calls return {sent:false, skipped:true, reason:...} and never
         crash. Status endpoint reports configured=false until real creds are set."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED: All notification endpoints working correctly. GET /api/notifications/status requires admin auth (401 without token), returns proper status with configured=false for placeholder credentials, includes all expected fields (enabled, configured, tenant_id_present, client_id_present, client_secret_present, sender_email, default_recipient, client_id_hint). POST /api/notifications/test gracefully skips with placeholder credentials, returns {sent:false, skipped:true, reason:'Microsoft Graph credentials not configured (placeholder values)'}. Project transitions trigger approval emails without crashing - graceful degradation working."

frontend:
  - task: "Royal Purple theme (#5C2B84 / #FFC000 / white)"
    implemented: true
    working: "NA"
    file: "frontend/src/lib/theme.jsx, frontend/src/index.css"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -agent: "main"
        -comment: "New theme key 'royal' added. Selectable in Settings → Appearance."

  - task: "Dashboard charts — colorful & minimalistic"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/DashboardPage.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -agent: "main"
        -comment: "10-color vibrant palette (orange/gold/green/brown/purple/olive/...).
         Vendor pie now has padding-angle, slice borders, percentage labels, formatted
         tooltip, and percentage list. Stage funnel bars are multi-color with right-side
         data labels. Line chart uses purple+gold strokes with rounded dots."

  - task: "PDF auto-parse panel inside New/Edit Project modal"
    implemented: true
    working: "NA"
    file: "frontend/src/components/ProjectFormModal.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Added top-of-modal panel: Choose PDF → preview shows PO type
         (Customer/Vendor) badge, confidence, key fields and milestone count.
         User clicks 'Apply to form' to populate empty form fields (manual edits
         preserved). Date strings normalised to YYYY-MM-DD. Existing Documents tab
         remains untouched."

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 2
  run_ui: false

test_plan:
  current_focus:
    - "Unified SAP Excel uploader (per-project /api/projects/{pid}/sap-upload + /api/uploads/template/sap-transactions)"
    - "Excel-based project autofill in New/Edit modal (/api/projects/parse-excel)"
    - "ProjectDetailPage crash fix on Revenue/Cost/Milestones tabs (Smart Airside Gate Solution)"
    - "Admin-only Delete project button on Project Detail header"
    - "Customer delete guard (block 409 when projects linked)"
    - "Revenue/Cost stat-tile chips on Project Detail header link to corresponding tab"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
        Iteration 3 - 6 new items shipped:
        1) NEW backend POST /api/projects/{pid}/sap-upload?kind=revenue|cost
           - parses unified 4-sheet SAP workbook (Revenue_SAP / Expenses_SAP / Supplier Mapping / Project Master)
           - matches rows by project's WBS Element (also accepts WBS prefixes so WSIN.000136.0001 flows into project on WSIN.000136)
           - inserts into revenue_lines / cost_lines, returns {matched, imported, skipped, wbs, kind}
           - test workbook: /tmp/template.xlsx imports 332 revenue + 1087 cost rows for project with wbs WSIN.000136.0001
        2) NEW GET /api/uploads/template/sap-transactions  (returns the 4-sheet empty template)
        3) NEW POST /api/projects/parse-excel?wbs=...  (Project Master autofill for the New/Edit modal — returns matched metadata or list of WBS candidates)
        4) Customer delete guard - DELETE /api/customers/{cid} now returns 409 if any project links to this customer
        5) Frontend crash fix on ProjectDetailPage Revenue/Cost/Milestones tabs - inrPerUsd was not propagated to child components
        6) Admin-only Delete button on Project Detail header (calls existing DELETE /api/projects/{pid})
        7) Revenue Plan / Cost Plan stat tiles are now clickable -> jump to corresponding tab
        8) ProjectFormModal now has dual smart-fill: PDF (Customer/Vendor PO) OR Excel (SAP Project Master)

        ⚠️ EXISTING TESTS THAT MUST NOT REGRESS:
        - parse-pdf endpoint (tested earlier)
        - notifications status / test (tested earlier)
        - PO classification (tested earlier)

backend:
  - task: "Customer delete guard (409 when linked projects exist)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "DELETE /api/customers/{cid} now blocks (409) if any project references this customer_id. Curl tested manually - returns 'Cannot delete... 2 project(s) are linked'."

  - task: "Unified SAP per-project upload (/api/projects/{pid}/sap-upload?kind=revenue|cost)"
    implemented: true
    working: true
    file: "backend/server.py, backend/sap_parser.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Reads unified 4-sheet workbook. Matches rows by project's WBS Element AND prefixes so WSIN.000136.0001 flows into a project anchored on WSIN.000136. Returns {matched, imported, skipped, wbs, kind}. Manual test on /tmp/template.xlsx: 332 revenue + 1087 cost imported."

  - task: "Excel autofill for project modal (/api/projects/parse-excel)"
    implemented: true
    working: true
    file: "backend/server.py, backend/sap_parser.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Reads Project Master sheet. With wbs query param, returns matched metadata (project_name, p&l, location, categories, business_category, etc.). Without wbs, returns candidates list. Returns shape compatible with ProjectFormModal preview UI."

  - task: "GET /api/uploads/template/sap-transactions (download empty SAP template)"
    implemented: true
    working: true
    file: "backend/server.py, backend/sap_parser.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Folded into existing /uploads/template/{entity} handler. Returns 4-sheet empty workbook (Expenses_SAP, Revenue_SAP, Supplier Mapping, Project Master). Manual test: 200 OK, 7295 bytes."

frontend:
  - task: "Fix ProjectDetailPage crash on Revenue/Cost/Milestones tabs"
    implemented: true
    working: true
    file: "frontend/src/pages/ProjectDetailPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "ROOT CAUSE: inrPerUsd was destructured only in parent ProjectDetailPage but referenced inside RevenueTab/CostTab/Milestones as a free variable -> ReferenceError when rows.map ran on populated projects (e.g. Smart Airside Gate Solution). Empty projects didn't crash because map skipped. Now passing inrPerUsd as prop. Verified via screenshot: all 3 tabs load on previously-crashing project."

  - task: "Admin-only Delete button on Project Detail page"
    implemented: true
    working: true
    file: "frontend/src/pages/ProjectDetailPage.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Visible only when user.role === 'admin'. Confirms before delete, navigates to /projects on success. Calls existing DELETE /api/projects/{pid}. data-testid: delete-project-btn. Verified: button visible in red on the project detail header."

  - task: "Revenue/Cost stat tiles clickable -> deep-link to tab"
    implemented: true
    working: true
    file: "frontend/src/pages/ProjectDetailPage.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Stat tiles for Revenue Plan and Cost Plan now show a small arrow + cursor pointer + hover highlight; clicking switches the active tab. data-testid: stat-revenue, stat-cost. Verified via screenshot."

  - task: "Per-project SAP Excel uploader UI (Revenue & Cost tabs)"
    implemented: true
    working: true
    file: "frontend/src/pages/ProjectDetailPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "New SapBulkUpload component renders inline next to 'Add Revenue/Cost' on each tab. Provides 'SAP template' download link + 'Import SAP Excel' button. Shows Imported/Matched/Skipped counters with WBS context. data-testid: sap-bulk-btn-revenue, sap-bulk-btn-cost, sap-bulk-input-revenue, sap-bulk-input-cost, sap-bulk-result-revenue, sap-bulk-result-cost."

  - task: "Project modal Excel auto-fill (SAP Project Master)"
    implemented: true
    working: true
    file: "frontend/src/components/ProjectFormModal.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -agent: "main"
        -comment: "Smart auto-fill panel now offers PDF AND Excel. Excel parses Project Master sheet. If WBS already in form, fetches metadata immediately. Otherwise shows candidate WBS list as a select; picking one fetches details. Apply only fills empty fields. data-testid: modal-xls-pick, modal-xls-input, xls-candidates, xls-wbs-select, xls-apply-btn, xls-parse-preview, xls-po-type."
        1) New backend endpoint POST /api/projects/parse-pdf (auth required, accepts
           multipart PDF, returns parsed fields incl. po_type/issuer/recipient/confidence
           + milestones). Does NOT write to DB.
        2) Royal Purple theme + colourful charts (frontend only, no test needed).
        3) Microsoft Graph email notifications module with graceful placeholder mode.
           - GET /api/notifications/status (admin) → returns configured flag (false now)
           - POST /api/notifications/test (admin) → with placeholder creds returns
             {sent:false, skipped:true, reason:"...not configured..."}
           - Approval request dispatches an email asynchronously (also skipped with
             placeholder creds).
        Please run backend tests focused on the 3 backend tasks above. Use admin
        credentials from /app/memory/test_credentials.md
        (admin@crackerpro.com / Admin@123). For the parse-pdf endpoint, please test
        with any small PDF (a generated multi-line text PDF is fine — it should still
        return 200 with parsed=null-ish fields and `warnings`).
    -agent: "testing"
    -message: |
        ✅ BACKEND TESTING COMPLETE - ALL 3 FEATURES WORKING PERFECTLY
        
        Comprehensive testing completed for all 3 newly added backend features:
        
        1. **POST /api/projects/parse-pdf** - ✅ FULLY FUNCTIONAL
           - Authentication: Properly requires auth (401 without token)
           - Validation: Correctly rejects non-PDF files (400) and empty files (400)
           - PDF Processing: Successfully parses valid PDFs with all expected fields
           - Database Safety: Confirmed NO database writes during parsing operations
           - Response Format: Returns proper structure with file_name, size, and parsed fields
        
        2. **Customer PO vs Vendor PO Classification** - ✅ FULLY FUNCTIONAL
           - Customer PO: Correctly identifies when WAISL is vendor/recipient
           - Vendor PO: Correctly identifies when WAISL is issuer/buyer
           - Unknown PO: Properly handles cases with no WAISL mention
           - Confidence Levels: Appropriate confidence scoring (high/medium/low)
        
        3. **Microsoft Graph Email Notifications** - ✅ FULLY FUNCTIONAL
           - Admin Authentication: Properly secured endpoints (401 without admin token)
           - Status Endpoint: Returns correct configuration status (configured=false with placeholders)
           - Test Endpoint: Gracefully skips with placeholder credentials
           - Approval Integration: Project transitions trigger emails without crashing
           - Graceful Degradation: No system crashes with placeholder credentials
        
        **Additional Verification:**
        - Existing login flow: ✅ Working
        - Projects listing: ✅ Working  
        - Project transitions: ✅ Working (approval emails gracefully skipped)
        - Backend service: ✅ Healthy and stable
        
        **Test Results: 17/17 tests passed (100% success rate)**
        All backend features are production-ready and working as designed.
