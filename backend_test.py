#!/usr/bin/env python3
"""
Comprehensive RBAC Backend Tests for CRacker Pro
Tests permanent admin protection, roles CRUD, permissions, and employee bulk upload
"""
import requests
import json
import io
from openpyxl import Workbook

# Read backend URL from frontend/.env
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip() + "/api"
            break

print(f"🔗 Backend URL: {BASE_URL}\n")

# Test credentials
ADMIN_CREDS = {"email": "admin@crackerpro.com", "password": "Admin@123"}
PERMANENT_ADMIN_1 = {"email": "rohit.kataria@waisldigital.com", "password": "RKataria@121"}
PERMANENT_ADMIN_2 = {"email": "tushar.sukhija@waisldigital.com", "password": "TSukhija@121"}

def login(creds):
    """Login and return token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        print(f"❌ Login failed for {creds['email']}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("access_token")

def get_headers(token):
    """Return auth headers"""
    return {"Authorization": f"Bearer {token}"}

# ============================================================
# TEST 1: Permanent admin login
# ============================================================
print("=" * 70)
print("TEST 1: Permanent Admin Login")
print("=" * 70)

# Test 1a: Rohit Kataria login
print("\n1a. Login as rohit.kataria@waisldigital.com")
token_rk = login(PERMANENT_ADMIN_1)
if token_rk:
    print(f"✅ Login successful, token received")
    # Get user info
    resp = requests.get(f"{BASE_URL}/auth/me", headers=get_headers(token_rk))
    if resp.status_code == 200:
        user = resp.json()
        if user.get("role") == "admin" and user.get("is_permanent_admin") == True:
            print(f"✅ User role=admin, is_permanent_admin=true")
        else:
            print(f"❌ Expected role=admin and is_permanent_admin=true, got: {user}")
    else:
        print(f"❌ Failed to get user info: {resp.status_code}")
else:
    print(f"❌ Login failed")

# Test 1b: Tushar Sukhija login
print("\n1b. Login as tushar.sukhija@waisldigital.com")
token_ts = login(PERMANENT_ADMIN_2)
if token_ts:
    print(f"✅ Login successful, token received")
    # Get user info
    resp = requests.get(f"{BASE_URL}/auth/me", headers=get_headers(token_ts))
    if resp.status_code == 200:
        user = resp.json()
        if user.get("role") == "admin" and user.get("is_permanent_admin") == True:
            print(f"✅ User role=admin, is_permanent_admin=true")
        else:
            print(f"❌ Expected role=admin and is_permanent_admin=true, got: {user}")
    else:
        print(f"❌ Failed to get user info: {resp.status_code}")
else:
    print(f"❌ Login failed")

# ============================================================
# TEST 2: Permanent admin protection
# ============================================================
print("\n" + "=" * 70)
print("TEST 2: Permanent Admin Protection")
print("=" * 70)

# Login as regular admin
admin_token = login(ADMIN_CREDS)
if not admin_token:
    print("❌ Cannot proceed - admin login failed")
    exit(1)

# Get list of users to find rohit.kataria's ID
print("\n2a. Get user list to find rohit.kataria's ID")
resp = requests.get(f"{BASE_URL}/admin/users", headers=get_headers(admin_token))
if resp.status_code == 200:
    users = resp.json()
    rk_user = next((u for u in users if u["email"] == "rohit.kataria@waisldigital.com"), None)
    if rk_user:
        rk_id = rk_user["id"]
        print(f"✅ Found rohit.kataria user with ID: {rk_id}")
        
        # Test 2b: Try to delete permanent admin
        print("\n2b. Try to DELETE permanent admin (should fail)")
        resp = requests.delete(f"{BASE_URL}/admin/users/{rk_id}", headers=get_headers(admin_token))
        if resp.status_code == 400:
            print(f"✅ DELETE blocked with 400: {resp.json().get('detail')}")
        else:
            print(f"❌ Expected 400, got {resp.status_code}: {resp.text}")
        
        # Test 2c: Try to change role
        print("\n2c. Try to change permanent admin role to 'finance' (should fail)")
        resp = requests.put(
            f"{BASE_URL}/admin/users/{rk_id}",
            headers=get_headers(admin_token),
            json={"role": "finance"}
        )
        if resp.status_code == 400:
            print(f"✅ Role change blocked with 400: {resp.json().get('detail')}")
        else:
            print(f"❌ Expected 400, got {resp.status_code}: {resp.text}")
        
        # Test 2d: Try to reset password
        print("\n2d. Try to reset permanent admin password (should fail)")
        resp = requests.post(
            f"{BASE_URL}/admin/users/reset-password",
            headers=get_headers(admin_token),
            json={"user_id": rk_id, "new_password": "NewPass@123"}
        )
        if resp.status_code == 400:
            print(f"✅ Password reset blocked with 400: {resp.json().get('detail')}")
        else:
            print(f"❌ Expected 400, got {resp.status_code}: {resp.text}")
    else:
        print(f"❌ Could not find rohit.kataria user in list")
else:
    print(f"❌ Failed to get user list: {resp.status_code}")

# ============================================================
# TEST 3: GET /api/me/permissions for admin
# ============================================================
print("\n" + "=" * 70)
print("TEST 3: Admin Permissions")
print("=" * 70)

print("\n3. GET /api/me/permissions as admin@crackerpro.com")
resp = requests.get(f"{BASE_URL}/me/permissions", headers=get_headers(admin_token))
if resp.status_code == 200:
    perms = resp.json()
    print(f"✅ Got permissions response")
    
    # Check is_admin
    if perms.get("is_admin") == True:
        print(f"✅ is_admin=true")
    else:
        print(f"❌ Expected is_admin=true, got: {perms.get('is_admin')}")
    
    # Check all 6 sections
    sections = ["dashboard", "pipeline", "projects", "change_requests", "customer_profile", "wbs_budget"]
    all_ok = True
    for section in sections:
        sec_perms = perms.get("permissions", {}).get(section, {})
        if sec_perms.get("can_view") == True and sec_perms.get("can_edit") == True and sec_perms.get("can_delete") == True:
            print(f"✅ {section}: can_view=true, can_edit=true, can_delete=true")
        else:
            print(f"❌ {section}: expected all true, got {sec_perms}")
            all_ok = False
    
    if all_ok:
        print(f"✅ All 6 sections have full permissions")
else:
    print(f"❌ Failed to get permissions: {resp.status_code} {resp.text}")

# ============================================================
# TEST 4: Roles CRUD
# ============================================================
print("\n" + "=" * 70)
print("TEST 4: Roles CRUD")
print("=" * 70)

# Test 4a: GET /api/roles
print("\n4a. GET /api/roles (any authenticated user)")
resp = requests.get(f"{BASE_URL}/roles", headers=get_headers(admin_token))
if resp.status_code == 200:
    roles = resp.json()
    print(f"✅ GET /api/roles returned 200 with {len(roles)} roles")
else:
    print(f"❌ GET /api/roles failed: {resp.status_code}")

# Test 4b: POST /api/roles (create custom role)
print("\n4b. POST /api/roles as admin (create custom role)")
role_payload = {
    "name": "Sales Viewer Test",
    "description": "test role",
    "permissions": {
        "projects": {"can_view": True, "can_edit": True},
        "pipeline": {"can_view": False, "can_edit": False},
        "dashboard": {"can_view": True, "can_edit": False}
    }
}
resp = requests.post(f"{BASE_URL}/roles", headers=get_headers(admin_token), json=role_payload)
if resp.status_code in [200, 201]:
    created_role = resp.json()
    role_id = created_role.get("id")
    print(f"✅ Role created with ID: {role_id}")
    
    # Verify fields
    if created_role.get("name") == "Sales Viewer Test":
        print(f"✅ Role name correct")
    else:
        print(f"❌ Role name mismatch: {created_role.get('name')}")
    
    if created_role.get("is_system") == False:
        print(f"✅ is_system=false")
    else:
        print(f"❌ Expected is_system=false, got: {created_role.get('is_system')}")
    
    # Check permissions persisted
    perms = created_role.get("permissions", {})
    if perms.get("projects", {}).get("can_view") == True and perms.get("projects", {}).get("can_edit") == True:
        print(f"✅ projects permissions persisted correctly")
    else:
        print(f"❌ projects permissions incorrect: {perms.get('projects')}")
    
    if perms.get("pipeline", {}).get("can_view") == False:
        print(f"✅ pipeline.can_view=false persisted")
    else:
        print(f"❌ pipeline.can_view should be false: {perms.get('pipeline')}")
    
    # Test 4c: PUT /api/roles/{id} (update role)
    print("\n4c. PUT /api/roles/{id} (update role)")
    update_payload = {
        "name": "Sales Viewer Test v2",
        "description": "updated test role",
        "permissions": {
            "projects": {"can_view": True, "can_edit": False},
            "pipeline": {"can_view": True, "can_edit": False},
            "dashboard": {"can_view": True, "can_edit": True}
        }
    }
    resp = requests.put(f"{BASE_URL}/roles/{role_id}", headers=get_headers(admin_token), json=update_payload)
    if resp.status_code == 200:
        updated_role = resp.json()
        if updated_role.get("name") == "Sales Viewer Test v2":
            print(f"✅ Role name updated to 'Sales Viewer Test v2'")
        else:
            print(f"❌ Role name not updated: {updated_role.get('name')}")
        
        # Check updated permissions
        perms = updated_role.get("permissions", {})
        if perms.get("projects", {}).get("can_edit") == False:
            print(f"✅ projects.can_edit updated to false")
        else:
            print(f"❌ projects.can_edit should be false: {perms.get('projects')}")
    else:
        print(f"❌ PUT /api/roles/{role_id} failed: {resp.status_code} {resp.text}")
    
    # Test 4d: DELETE /api/roles/{id}
    print("\n4d. DELETE /api/roles/{id}")
    resp = requests.delete(f"{BASE_URL}/roles/{role_id}", headers=get_headers(admin_token))
    if resp.status_code == 200:
        print(f"✅ Role deleted successfully")
        
        # Verify it's gone
        resp = requests.get(f"{BASE_URL}/roles", headers=get_headers(admin_token))
        if resp.status_code == 200:
            roles = resp.json()
            if not any(r.get("id") == role_id for r in roles):
                print(f"✅ Role no longer in list")
            else:
                print(f"❌ Role still in list after deletion")
    else:
        print(f"❌ DELETE /api/roles/{role_id} failed: {resp.status_code} {resp.text}")
    
else:
    print(f"❌ POST /api/roles failed: {resp.status_code} {resp.text}")
    role_id = None

# Test 4e: Duplicate name POST
print("\n4e. POST /api/roles with duplicate name (should fail with 409)")
dup_payload = {
    "name": "Sales Viewer Test",
    "description": "duplicate",
    "permissions": {"dashboard": {"can_view": True, "can_edit": False}}
}
resp = requests.post(f"{BASE_URL}/roles", headers=get_headers(admin_token), json=dup_payload)
if resp.status_code == 409:
    print(f"✅ Duplicate name blocked with 409: {resp.json().get('detail')}")
else:
    print(f"❌ Expected 409, got {resp.status_code}: {resp.text}")

# Test 4f: Non-admin access (create a non-admin user first)
print("\n4f. Non-admin access to roles endpoints (should fail with 403)")
# Create a non-admin user
non_admin_payload = {
    "email": "nonadmin.test@example.com",
    "password": "Test@1234",
    "name": "Non Admin Test",
    "role": "finance",
    "location": "Test",
    "reporting_manager_email": None,
    "role_id": None
}
resp = requests.post(f"{BASE_URL}/admin/users", headers=get_headers(admin_token), json=non_admin_payload)
if resp.status_code in [200, 201]:
    non_admin_user = resp.json()
    non_admin_id = non_admin_user.get("id")
    print(f"✅ Created non-admin user: {non_admin_user.get('email')}")
    
    # Login as non-admin
    non_admin_token = login({"email": "nonadmin.test@example.com", "password": "Test@1234"})
    if non_admin_token:
        print(f"✅ Non-admin login successful")
        
        # Try POST /api/roles
        test_role = {
            "name": "Should Fail",
            "description": "test",
            "permissions": {"dashboard": {"can_view": True, "can_edit": False}}
        }
        resp = requests.post(f"{BASE_URL}/roles", headers=get_headers(non_admin_token), json=test_role)
        if resp.status_code in [403, 401]:
            print(f"✅ Non-admin POST /api/roles blocked with {resp.status_code}")
        else:
            print(f"❌ Expected 403/401, got {resp.status_code}: {resp.text}")
        
        # Try PUT /api/roles (if we have a role_id)
        if role_id:
            resp = requests.put(f"{BASE_URL}/roles/{role_id}", headers=get_headers(non_admin_token), json=test_role)
            if resp.status_code in [403, 401]:
                print(f"✅ Non-admin PUT /api/roles blocked with {resp.status_code}")
            else:
                print(f"❌ Expected 403/401, got {resp.status_code}: {resp.text}")
        
        # Try DELETE /api/roles
        if role_id:
            resp = requests.delete(f"{BASE_URL}/roles/{role_id}", headers=get_headers(non_admin_token))
            if resp.status_code in [403, 401]:
                print(f"✅ Non-admin DELETE /api/roles blocked with {resp.status_code}")
            else:
                print(f"❌ Expected 403/401, got {resp.status_code}: {resp.text}")
    else:
        print(f"❌ Non-admin login failed")
    
    # Cleanup: delete non-admin user
    requests.delete(f"{BASE_URL}/admin/users/{non_admin_id}", headers=get_headers(admin_token))
else:
    print(f"❌ Failed to create non-admin user: {resp.status_code} {resp.text}")

# ============================================================
# TEST 5: Role assignment & permissions enforcement
# ============================================================
print("\n" + "=" * 70)
print("TEST 5: Role Assignment & Permissions Enforcement")
print("=" * 70)

# Test 5a: Create user without role_id
print("\n5a. Create user without role_id")
test_user_payload = {
    "email": "rbac.tester@example.com",
    "password": "Test@1234",
    "name": "RBAC Tester",
    "role": "finance",
    "location": "Test",
    "reporting_manager_email": None,
    "role_id": None
}
resp = requests.post(f"{BASE_URL}/admin/users", headers=get_headers(admin_token), json=test_user_payload)
if resp.status_code in [200, 201]:
    test_user = resp.json()
    test_user_id = test_user.get("id")
    print(f"✅ Created user: {test_user.get('email')}")
    
    # Login as test user
    test_token = login({"email": "rbac.tester@example.com", "password": "Test@1234"})
    if test_token:
        print(f"✅ Test user login successful")
        
        # Get permissions (should default to dashboard.can_view=true)
        resp = requests.get(f"{BASE_URL}/me/permissions", headers=get_headers(test_token))
        if resp.status_code == 200:
            perms = resp.json()
            print(f"✅ Got permissions for test user")
            
            if perms.get("is_admin") == False:
                print(f"✅ is_admin=false")
            else:
                print(f"❌ Expected is_admin=false, got: {perms.get('is_admin')}")
            
            # Check default permissions (dashboard.can_view=true, rest false)
            dash_perms = perms.get("permissions", {}).get("dashboard", {})
            if dash_perms.get("can_view") == True:
                print(f"✅ Default: dashboard.can_view=true")
            else:
                print(f"❌ Expected dashboard.can_view=true, got: {dash_perms}")
            
            # Check other sections are false
            projects_perms = perms.get("permissions", {}).get("projects", {})
            if projects_perms.get("can_view") == False:
                print(f"✅ Default: projects.can_view=false")
            else:
                print(f"❌ Expected projects.can_view=false, got: {projects_perms}")
        else:
            print(f"❌ Failed to get permissions: {resp.status_code}")
    else:
        print(f"❌ Test user login failed")
    
    # Test 5b: Create role with only customer_profile.can_view=true
    print("\n5b. Create role with customer_profile.can_view=true")
    custom_role_payload = {
        "name": "Customer Profile Viewer",
        "description": "Can only view customer profile",
        "permissions": {
            "customer_profile": {"can_view": True, "can_edit": False},
            "dashboard": {"can_view": False, "can_edit": False},
            "projects": {"can_view": False, "can_edit": False},
            "pipeline": {"can_view": False, "can_edit": False},
            "change_requests": {"can_view": False, "can_edit": False},
            "wbs_budget": {"can_view": False, "can_edit": False}
        }
    }
    resp = requests.post(f"{BASE_URL}/roles", headers=get_headers(admin_token), json=custom_role_payload)
    if resp.status_code in [200, 201]:
        custom_role = resp.json()
        custom_role_id = custom_role.get("id")
        print(f"✅ Created custom role: {custom_role.get('name')} (ID: {custom_role_id})")
        
        # Assign role to test user
        print("\n5c. Assign custom role to test user")
        resp = requests.put(
            f"{BASE_URL}/admin/users/{test_user_id}",
            headers=get_headers(admin_token),
            json={"role_id": custom_role_id}
        )
        if resp.status_code == 200:
            print(f"✅ Role assigned to user")
            
            # Login again and check permissions
            test_token = login({"email": "rbac.tester@example.com", "password": "Test@1234"})
            if test_token:
                resp = requests.get(f"{BASE_URL}/me/permissions", headers=get_headers(test_token))
                if resp.status_code == 200:
                    perms = resp.json()
                    print(f"✅ Got updated permissions")
                    
                    # Check customer_profile.can_view=true
                    cp_perms = perms.get("permissions", {}).get("customer_profile", {})
                    if cp_perms.get("can_view") == True and cp_perms.get("can_edit") == False:
                        print(f"✅ customer_profile.can_view=true, can_edit=false")
                    else:
                        print(f"❌ Expected customer_profile.can_view=true, got: {cp_perms}")
                    
                    # Check dashboard.can_view=false (overridden by role)
                    dash_perms = perms.get("permissions", {}).get("dashboard", {})
                    if dash_perms.get("can_view") == False:
                        print(f"✅ dashboard.can_view=false (overridden by role)")
                    else:
                        print(f"❌ Expected dashboard.can_view=false, got: {dash_perms}")
                    
                    # Verify ALL can_delete=false for non-admin
                    all_delete_false = True
                    for section in ["dashboard", "pipeline", "projects", "change_requests", "customer_profile", "wbs_budget"]:
                        sec_perms = perms.get("permissions", {}).get(section, {})
                        if sec_perms.get("can_delete") != False:
                            print(f"❌ {section}.can_delete should be false, got: {sec_perms.get('can_delete')}")
                            all_delete_false = False
                    if all_delete_false:
                        print(f"✅ All sections have can_delete=false for non-admin")
                else:
                    print(f"❌ Failed to get updated permissions: {resp.status_code}")
        else:
            print(f"❌ Failed to assign role: {resp.status_code} {resp.text}")
        
        # Cleanup: delete custom role
        requests.delete(f"{BASE_URL}/roles/{custom_role_id}", headers=get_headers(admin_token))
    else:
        print(f"❌ Failed to create custom role: {resp.status_code} {resp.text}")
    
    # Cleanup: delete test user
    requests.delete(f"{BASE_URL}/admin/users/{test_user_id}", headers=get_headers(admin_token))
else:
    print(f"❌ Failed to create test user: {resp.status_code} {resp.text}")

# ============================================================
# TEST 6: Employee bulk-upload preserves permanent admins
# ============================================================
print("\n" + "=" * 70)
print("TEST 6: Employee Bulk Upload Preserves Permanent Admins")
print("=" * 70)

# Test 6a: Verify permanent admin employees exist
print("\n6a. GET /api/employees - verify permanent admin employees exist")
resp = requests.get(f"{BASE_URL}/employees", headers=get_headers(admin_token))
if resp.status_code == 200:
    employees = resp.json()
    print(f"✅ Got {len(employees)} employees")
    
    rk_emp = next((e for e in employees if e.get("email_id", "").lower() == "rohit.kataria@waisldigital.com"), None)
    ts_emp = next((e for e in employees if e.get("email_id", "").lower() == "tushar.sukhija@waisldigital.com"), None)
    
    if rk_emp:
        print(f"✅ Found rohit.kataria@waisldigital.com employee")
    else:
        print(f"❌ rohit.kataria@waisldigital.com employee not found")
    
    if ts_emp:
        print(f"✅ Found tushar.sukhija@waisldigital.com employee")
    else:
        print(f"❌ tushar.sukhija@waisldigital.com employee not found")
else:
    print(f"❌ Failed to get employees: {resp.status_code}")

# Test 6b: Create tiny xlsx with one new employee and upload in replace mode
print("\n6b. Upload tiny xlsx with mode=replace (should preserve permanent admins)")
wb = Workbook()
ws = wb.active
ws.append(["Employee No", "Email ID", "Status", "Joining Date", "Exit Date", "Employement Type", 
           "Employee Name", "Role (as per Zoho)", "L1 Manager", "Location", "Department", "Sub Department"])
ws.append(["W9999", "new.employee@example.com", "Active", "01-01-2026", None, "Employee",
           "New Employee Test", "Test Role", "W0989", "Test Location", "Test Dept", "Test Sub"])

# Save to BytesIO
excel_buffer = io.BytesIO()
wb.save(excel_buffer)
excel_buffer.seek(0)

resp = requests.post(
    f"{BASE_URL}/employees/bulk-upload?mode=replace",
    headers=get_headers(admin_token),
    files={"file": ("test_employees.xlsx", excel_buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
)
if resp.status_code == 200:
    result = resp.json()
    print(f"✅ Bulk upload successful: {result}")
    
    # Test 6c: Verify permanent admin employees still exist
    print("\n6c. GET /api/employees again - verify permanent admins still exist")
    resp = requests.get(f"{BASE_URL}/employees", headers=get_headers(admin_token))
    if resp.status_code == 200:
        employees = resp.json()
        print(f"✅ Got {len(employees)} employees after replace")
        
        rk_emp = next((e for e in employees if e.get("email_id", "").lower() == "rohit.kataria@waisldigital.com"), None)
        ts_emp = next((e for e in employees if e.get("email_id", "").lower() == "tushar.sukhija@waisldigital.com"), None)
        new_emp = next((e for e in employees if e.get("email_id", "").lower() == "new.employee@example.com"), None)
        
        if rk_emp:
            print(f"✅ rohit.kataria@waisldigital.com STILL EXISTS after replace")
        else:
            print(f"❌ rohit.kataria@waisldigital.com MISSING after replace")
        
        if ts_emp:
            print(f"✅ tushar.sukhija@waisldigital.com STILL EXISTS after replace")
        else:
            print(f"❌ tushar.sukhija@waisldigital.com MISSING after replace")
        
        if new_emp:
            print(f"✅ New employee added successfully")
        else:
            print(f"❌ New employee not found")
    else:
        print(f"❌ Failed to get employees: {resp.status_code}")
else:
    print(f"❌ Bulk upload failed: {resp.status_code} {resp.text}")

# ============================================================
# TEST 7: Regression smoke tests
# ============================================================
print("\n" + "=" * 70)
print("TEST 7: Regression Smoke Tests")
print("=" * 70)

# Test 7a: GET /api/projects
print("\n7a. GET /api/projects")
resp = requests.get(f"{BASE_URL}/projects", headers=get_headers(admin_token))
if resp.status_code == 200:
    projects = resp.json()
    print(f"✅ GET /api/projects returned 200 with {len(projects)} projects")
else:
    print(f"❌ GET /api/projects failed: {resp.status_code}")

# Test 7b: GET /api/pipeline
print("\n7b. GET /api/pipeline")
resp = requests.get(f"{BASE_URL}/pipeline", headers=get_headers(admin_token))
if resp.status_code == 200:
    pipeline = resp.json()
    print(f"✅ GET /api/pipeline returned 200 with {len(pipeline)} items")
else:
    print(f"❌ GET /api/pipeline failed: {resp.status_code}")

# Test 7c: GET /api/notifications/status
print("\n7c. GET /api/notifications/status (admin)")
resp = requests.get(f"{BASE_URL}/notifications/status", headers=get_headers(admin_token))
if resp.status_code == 200:
    status = resp.json()
    if status.get("configured") == False:
        print(f"✅ GET /api/notifications/status returned 200 with configured=false")
    else:
        print(f"⚠️  GET /api/notifications/status returned 200 but configured={status.get('configured')}")
else:
    print(f"❌ GET /api/notifications/status failed: {resp.status_code}")

print("\n" + "=" * 70)
print("🎉 ALL TESTS COMPLETED")
print("=" * 70)
