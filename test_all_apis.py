"""
HRMS Full API Test & Database Dummy Data Seeder
==============================================
Tests all REST API endpoints (GET, POST, PUT, PATCH, DELETE) across all 12 modules,
seeds realistic dummy data, and saves everything directly to the PostgreSQL database.

Usage:
  # Run directly via ASGI / TestClient against the PostgreSQL database:
  python3 test_all_apis.py

  # Or run against a running server:
  python3 test_all_apis.py --url http://localhost:8000
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime, date, timedelta, time
import json
import httpx

# Ensure app package is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# ANSI Colors for beautiful terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


class APITester:
    def __init__(self, base_url: str = None, client: httpx.AsyncClient = None):
        self.client = client
        self.base_url = base_url or "http://testserver"
        self.token = None
        self.headers = {}
        self.results = []
        self.created_ids = {}

    def set_token(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def log_step(self, module: str, action: str, method: str, endpoint: str, status_code: int, expected: int, resp_data=None):
        passed = (status_code == expected) or (expected == 200 and status_code in [200, 201])
        status_icon = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.FAIL}✗ FAIL ({status_code}){Colors.END}"
        print(f"  {status_icon} [{method:6}] {endpoint:50} - {action}")
        self.results.append({
            "module": module,
            "action": action,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "passed": passed,
            "response": resp_data
        })
        if not passed:
            print(f"     {Colors.FAIL}Error response: {resp_data}{Colors.END}")

    async def request(self, method: str, path: str, json_body=None, params=None, expected_status=200, module=""):
        url = f"{self.base_url}/api/v1{path}"
        try:
            resp = await self.client.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
                headers=self.headers
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text

            await self.log_step(module, path, method, path, resp.status_code, expected_status, data)
            return resp.status_code, data
        except Exception as e:
            print(f"     {Colors.FAIL}Request exception on [{method}] {path}: {e}{Colors.END}")
            self.results.append({
                "module": module,
                "action": path,
                "method": method,
                "endpoint": path,
                "status_code": 500,
                "passed": False,
                "response": str(e)
            })
            return 500, str(e)


async def run_full_suite(base_url_arg: str = None):
    print(f"\n{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}    Keka HRMS - Complete End-to-End API Test & DB Data Seeder        {Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════{Colors.END}\n")

    import app.db.session as db_session
    from app.db.session import Base
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.main import app

    # Check if configured PostgreSQL is reachable, otherwise fallback to local async DB
    use_sqlite = False
    try:
        async with db_session.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"{Colors.GREEN}✓ Connected to PostgreSQL database ({db_session.settings.POSTGRES_SERVER}:{db_session.settings.POSTGRES_PORT}/{db_session.settings.POSTGRES_DB}){Colors.END}")
    except Exception as e:
        print(f"{Colors.WARNING}⚠ PostgreSQL not reachable at {db_session.settings.POSTGRES_SERVER}:{db_session.settings.POSTGRES_PORT} ({e}){Colors.END}")
        print(f"{Colors.CYAN}ℹ Switching test suite to local Async SQLite (test_hrms.db) for immediate full validation...{Colors.END}")
        use_sqlite = True
        if os.path.exists("./test_hrms.db"):
            try:
                os.remove("./test_hrms.db")
            except Exception:
                pass
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///./test_hrms.db", echo=False, future=True)
        db_session.engine = sqlite_engine
        db_session.AsyncSessionLocal = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
        async with db_session.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"{Colors.GREEN}✓ Initialized all module tables in fresh test database successfully!{Colors.END}")

    transport = None
    if not base_url_arg:
        transport = httpx.ASGITransport(app=app)
        async_client = httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0)
    else:
        async_client = httpx.AsyncClient(base_url=base_url_arg, timeout=60.0)

    async with async_client as client:
        tester = APITester(base_url=base_url_arg or "http://testserver", client=client)

        timestamp_suffix = datetime.now().strftime("%H%M%S")
        company_name = f"Nexus Tech {timestamp_suffix}"
        admin_email = f"admin_{timestamp_suffix}@nexustech.com"
        admin_password = "Password@123"

        # ─────────────────────────────────────────────────────────────
        # 1. TENANT REGISTRATION & AUTHENTICATION
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 1. SaaS Multi-Tenancy & Authentication{Colors.END}")
        
        # Register Company
        code, reg_data = await tester.request(
            "POST", "/tenants/register",
            json_body={
                "company_name": company_name,
                "admin_email": admin_email,
                "admin_first_name": "Alex",
                "admin_last_name": "Vance",
                "admin_password": admin_password
            },
            expected_status=201,
            module="Tenants"
        )

        # Login to get JWT Token
        code, login_data = await tester.request(
            "POST", "/auth/login",
            json_body={
                "company_name": company_name,
                "email": admin_email,
                "password": admin_password
            },
            expected_status=200,
            module="Authentication"
        )
        token = login_data.get("access_token") if isinstance(login_data, dict) else None
        if not token:
            print(f"{Colors.FAIL}Failed to authenticate. Stopping tests.{Colors.END}")
            return
        tester.set_token(token)
        print(f"     {Colors.GREEN}✓ Authenticated successfully as {admin_email}{Colors.END}")

        # Verify /auth/me
        await tester.request("GET", "/auth/me", expected_status=200, module="Authentication")

        # ─────────────────────────────────────────────────────────────
        # 2. CORE HR & ORGANIZATION
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 2. Core HR & Organization Structure{Colors.END}")

        # Departments (CRUD)
        _, dept1 = await tester.request("POST", "/core/departments/", json_body={"name": f"Engineering {timestamp_suffix}", "description": "Software Engineering & IT"}, expected_status=201, module="Core HR")
        _, dept2 = await tester.request("POST", "/core/departments/", json_body={"name": f"Human Resources {timestamp_suffix}", "description": "People Ops"}, expected_status=201, module="Core HR")
        dept_id = dept1.get("id") if isinstance(dept1, dict) else 1

        await tester.request("GET", "/core/departments/", expected_status=200, module="Core HR")
        await tester.request("GET", f"/core/departments/{dept_id}", expected_status=200, module="Core HR")
        await tester.request("PUT", f"/core/departments/{dept_id}", json_body={"name": f"Core Engineering {timestamp_suffix}", "description": "R&D and Product"}, expected_status=200, module="Core HR")
        await tester.request("PATCH", f"/core/departments/{dept_id}", json_body={"description": "Software & AI Engineering"}, expected_status=200, module="Core HR")

        # Designations (CRUD)
        _, desig1 = await tester.request("POST", "/core/designations/", json_body={"title": f"Senior Software Engineer {timestamp_suffix}", "description": "Full Stack Dev", "department_id": dept_id}, expected_status=201, module="Core HR")
        desig_id = desig1.get("id") if isinstance(desig1, dict) else 1
        await tester.request("GET", "/core/designations/", expected_status=200, module="Core HR")
        await tester.request("GET", f"/core/designations/{desig_id}", expected_status=200, module="Core HR")
        await tester.request("PATCH", f"/core/designations/{desig_id}", json_body={"description": "Lead Full Stack Architect"}, expected_status=200, module="Core HR")

        # Work Locations (CRUD)
        _, loc1 = await tester.request("POST", "/core/locations/", json_body={"name": f"HQ - Bengaluru {timestamp_suffix}", "address": "Indiranagar 100ft Rd", "city": "Bengaluru", "state": "Karnataka", "pincode": "560038"}, expected_status=201, module="Core HR")
        loc_id = loc1.get("id") if isinstance(loc1, dict) else 1
        await tester.request("GET", "/core/locations/", expected_status=200, module="Core HR")
        await tester.request("GET", f"/core/locations/{loc_id}", expected_status=200, module="Core HR")

        # Employees (CRUD)
        emp_email = f"sarah_{timestamp_suffix}@nexustech.com"
        _, emp1 = await tester.request("POST", "/core/employees/", json_body={
            "email": emp_email,
            "password": "Password@123",
            "first_name": "Sarah",
            "last_name": "Connor",
            "phone_number": "+919876543210",
            "job_title": "Senior Engineer",
            "employee_code": f"EMP-{timestamp_suffix}",
            "department_id": dept_id,
            "designation_id": desig_id,
            "work_location_id": loc_id,
            "is_active": True
        }, expected_status=201, module="Core HR")
        emp_id = emp1.get("id") if isinstance(emp1, dict) else 1
        await tester.request("GET", "/core/employees/", expected_status=200, module="Core HR")
        await tester.request("GET", f"/core/employees/{emp_id}", expected_status=200, module="Core HR")
        await tester.request("PATCH", f"/core/employees/{emp_id}", json_body={"job_title": "Principal Staff Engineer"}, expected_status=200, module="Core HR")

        # ─────────────────────────────────────────────────────────────
        # 3. EMPLOYEE PROFILES & DOCUMENTS
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 3. Employee Profiles, Documents & Org Tree{Colors.END}")

        # 1. Admin Profile
        admin_uid = login_data.get("user_id", 1)
        await tester.request("POST", "/profiles/", json_body={
            "user_id": admin_uid,
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "marital_status": "single",
            "nationality": "Indian",
            "blood_group": "A+",
            "phone_number": "+919988776655",
            "personal_email": "admin.personal@gmail.com",
            "city": "Bengaluru",
            "state": "Karnataka",
            "employment_type": "full_time",
            "date_of_joining": "2020-01-01",
            "skills": "Leadership, System Architecture, HR Operations"
        }, expected_status=201, module="Employee Profiles")

        # 2. Employee Profile
        _, prof1 = await tester.request("POST", "/profiles/", json_body={
            "user_id": emp_id,
            "date_of_birth": "1994-06-15",
            "gender": "female",
            "marital_status": "single",
            "nationality": "Indian",
            "blood_group": "O+",
            "phone_number": "+919876543210",
            "personal_email": "sarah.personal@gmail.com",
            "city": "Bengaluru",
            "state": "Karnataka",
            "employment_type": "full_time",
            "date_of_joining": "2023-01-10",
            "skills": "Python, FastAPI, React, PostgreSQL, Docker"
        }, expected_status=201, module="Employee Profiles")
        prof_id = prof1.get("id") if isinstance(prof1, dict) else 1

        await tester.request("GET", "/profiles/me", expected_status=200, module="Employee Profiles")
        await tester.request("GET", "/profiles/directory/all", expected_status=200, module="Employee Profiles")
        await tester.request("GET", "/profiles/org-tree", expected_status=200, module="Employee Profiles")
        await tester.request("GET", f"/profiles/by-user/{emp_id}", expected_status=200, module="Employee Profiles")

        # Sub-resources: Emergency contacts, Documents, Education, Experience
        await tester.request("POST", f"/profiles/{prof_id}/emergency-contacts", json_body={"name": "John Connor", "relation_type": "Father", "phone_number": "+919876543299"}, expected_status=201, module="Employee Profiles")
        await tester.request("GET", f"/profiles/{prof_id}/emergency-contacts", expected_status=200, module="Employee Profiles")

        await tester.request("POST", f"/profiles/{prof_id}/education", json_body={"degree": "B.Tech in Computer Science", "institution": "IIT Madras", "start_year": 2012, "end_year": 2016, "is_highest": True}, expected_status=201, module="Employee Profiles")
        await tester.request("GET", f"/profiles/{prof_id}/education", expected_status=200, module="Employee Profiles")

        await tester.request("POST", f"/profiles/{prof_id}/experience", json_body={"company_name": "Google", "job_title": "Software Engineer II", "start_date": "2016-07-01", "end_date": "2022-12-31", "is_current": False, "location": "Bengaluru"}, expected_status=201, module="Employee Profiles")
        await tester.request("GET", f"/profiles/{prof_id}/experience", expected_status=200, module="Employee Profiles")

        # ─────────────────────────────────────────────────────────────
        # 4. TIME & ATTENDANCE
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 4. Time & Attendance Management{Colors.END}")

        # Shifts & Geofences
        _, shift1 = await tester.request("POST", "/attendance/shifts/", json_body={"name": f"General Shift {timestamp_suffix}", "start_time": "09:00:00", "end_time": "18:00:00", "grace_period_mins": 15, "is_default": True}, expected_status=201, module="Attendance")
        shift_id = shift1.get("id") if isinstance(shift1, dict) else 1
        await tester.request("GET", "/attendance/shifts/", expected_status=200, module="Attendance")

        _, geo1 = await tester.request("POST", "/attendance/geofences/", json_body={"name": "Bengaluru Main Campus", "latitude": 12.9716, "longitude": 77.5946, "radius_meters": 200.0}, expected_status=201, module="Attendance")
        await tester.request("GET", "/attendance/geofences/", expected_status=200, module="Attendance")

        # Punch In & Out
        await tester.request("POST", "/attendance/punch-in", json_body={"latitude": 12.9716, "longitude": 77.5946, "note": "Clocking in from office desk"}, expected_status=200, module="Attendance")
        await tester.request("POST", "/attendance/punch-out", json_body={"latitude": 12.9716, "longitude": 77.5946, "note": "End of day clockout"}, expected_status=200, module="Attendance")

        # Logs & Filters
        await tester.request("GET", "/attendance/logs/", expected_status=200, module="Attendance")
        await tester.request("GET", "/attendance/logs/my", expected_status=200, module="Attendance")

        # Attendance Regularization
        today_str = date.today().isoformat()
        _, reg1 = await tester.request("POST", "/attendance/regularizations/", json_body={"date": today_str, "requested_punch_in": f"{today_str}T09:00:00Z", "requested_punch_out": f"{today_str}T18:00:00Z", "reason": "Biometric scanner device connectivity issue"}, expected_status=201, module="Attendance")
        reg_id = reg1.get("id") if isinstance(reg1, dict) else 1
        await tester.request("GET", "/attendance/regularizations/", expected_status=200, module="Attendance")
        await tester.request("PATCH", f"/attendance/regularizations/{reg_id}/approve", json_body={"approver_comment": "Approved regularization"}, expected_status=200, module="Attendance")

        # Overtime Request
        _, ot1 = await tester.request("POST", "/attendance/overtime/", json_body={"date": today_str, "overtime_hours": 2.5, "reason": "Production deployment release support"}, expected_status=201, module="Attendance")
        ot_id = ot1.get("id") if isinstance(ot1, dict) else 1
        await tester.request("GET", "/attendance/overtime/", expected_status=200, module="Attendance")
        await tester.request("PATCH", f"/attendance/overtime/{ot_id}/approve", json_body={"approver_comment": "Approved OT for production support"}, expected_status=200, module="Attendance")

        # ─────────────────────────────────────────────────────────────
        # 5. LEAVE & ABSENCE MANAGEMENT
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 5. Leave & Absence Management{Colors.END}")

        # Leave Types
        _, lt1 = await tester.request("POST", "/leave/types/", json_body={"name": f"Casual Leave {timestamp_suffix}", "code": f"CL_{timestamp_suffix}", "default_annual_quota": 12.0, "is_paid": True}, expected_status=201, module="Leave")
        _, lt2 = await tester.request("POST", "/leave/types/", json_body={"name": f"Sick Leave {timestamp_suffix}", "code": f"SL_{timestamp_suffix}", "default_annual_quota": 8.0, "is_paid": True}, expected_status=201, module="Leave")
        lt_id = lt1.get("id") if isinstance(lt1, dict) else 1
        await tester.request("GET", "/leave/types/", expected_status=200, module="Leave")

        # Allocate Annual Balances
        await tester.request("POST", "/leave/balances/allocate-annual", expected_status=200, module="Leave")
        await tester.request("GET", "/leave/balances/", expected_status=200, module="Leave")
        await tester.request("GET", "/leave/balances/my", expected_status=200, module="Leave")

        # Leave Requests
        next_week = (date.today() + timedelta(days=7)).isoformat()
        _, lreq1 = await tester.request("POST", "/leave/requests/", json_body={
            "leave_type_id": lt_id,
            "start_date": next_week,
            "end_date": next_week,
            "days_count": 1.0,
            "reason": "Family function personal leave"
        }, expected_status=201, module="Leave")
        lreq_id = lreq1.get("id") if isinstance(lreq1, dict) else 1

        await tester.request("GET", "/leave/requests/", expected_status=200, module="Leave")
        await tester.request("GET", "/leave/requests/my", expected_status=200, module="Leave")
        await tester.request("PATCH", f"/leave/requests/{lreq_id}/approve", expected_status=200, module="Leave")

        # Holidays
        await tester.request("POST", "/leave/holidays/", json_body={"name": "New Year Holiday", "date": "2026-01-01", "description": "National Holiday"}, expected_status=201, module="Leave")
        await tester.request("GET", "/leave/holidays/", expected_status=200, module="Leave")

        # Leave Encashment
        _, enc1 = await tester.request("POST", "/leave/encashments/", json_body={"leave_type_id": lt_id, "days_requested": 2.0}, expected_status=201, module="Leave")
        enc_id = enc1.get("id") if isinstance(enc1, dict) else 1
        await tester.request("PATCH", f"/leave/encashments/{enc_id}/approve", json_body={"amount": 5000.0, "comments": "Encashment processed"}, expected_status=200, module="Leave")

        # ─────────────────────────────────────────────────────────────
        # 6. PAYROLL & COMPENSATION
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 6. Payroll, Salary Structures & Payslips{Colors.END}")

        # Components
        _, c1 = await tester.request("POST", "/payroll/components/", json_body={"name": f"Basic Salary {timestamp_suffix}", "code": f"BASIC_{timestamp_suffix}", "component_type": "earning", "calculation_type": "fixed", "is_taxable": True}, expected_status=201, module="Payroll")
        _, c2 = await tester.request("POST", "/payroll/components/", json_body={"name": f"House Rent Allowance {timestamp_suffix}", "code": f"HRA_{timestamp_suffix}", "component_type": "earning", "calculation_type": "percentage_of_basic", "default_value": 40.0}, expected_status=201, module="Payroll")
        _, c3 = await tester.request("POST", "/payroll/components/", json_body={"name": f"Provident Fund {timestamp_suffix}", "code": f"PF_{timestamp_suffix}", "component_type": "deduction", "calculation_type": "fixed", "is_statutory": True}, expected_status=201, module="Payroll")
        await tester.request("GET", "/payroll/components/", expected_status=200, module="Payroll")

        # Structures
        _, struct1 = await tester.request("POST", "/payroll/structures/", json_body={"name": f"Standard Tech CTC {timestamp_suffix}", "description": "Standard software employee package"}, expected_status=201, module="Payroll")
        struct_id = struct1.get("id") if isinstance(struct1, dict) else 1
        await tester.request("GET", "/payroll/structures/", expected_status=200, module="Payroll")

        # Assign Employee Salary
        await tester.request("POST", "/payroll/employee-salaries/", json_body={
            "employee_id": emp_id,
            "structure_id": struct_id,
            "annual_ctc": 1800000.0,
            "monthly_gross": 150000.0,
            "basic_salary": 60000.0,
            "effective_from": "2026-01-01",
            "bank_name": "HDFC Bank",
            "account_number": "50100234567890",
            "ifsc_code": "HDFC0001234",
            "pan_number": "ABCDE1234F",
            "tax_regime": "new"
        }, expected_status=201, module="Payroll")
        await tester.request("GET", "/payroll/employee-salaries/", expected_status=200, module="Payroll")

        # Process Payroll Run
        curr_month = date.today().month
        curr_year = date.today().year
        _, run1 = await tester.request("POST", "/payroll/runs/process", json_body={"month": curr_month, "year": curr_year}, expected_status=201, module="Payroll")
        run_id = (run1.get("id") if (isinstance(run1, dict) and run1.get("id")) else 1)

        await tester.request("GET", "/payroll/runs/", expected_status=200, module="Payroll")
        await tester.request("GET", "/payroll/payslips/", expected_status=200, module="Payroll")
        await tester.request("PATCH", f"/payroll/runs/{run_id}/approve", expected_status=200, module="Payroll")
        await tester.request("PATCH", f"/payroll/runs/{run_id}/pay", expected_status=200, module="Payroll")

        # Form 12BB Declaration
        _, d12 = await tester.request("POST", "/payroll/declarations/", json_body={
            "financial_year": "2026-2027",
            "section_80c": 150000.0,
            "section_80d": 25000.0,
            "hra_rent_paid": 240000.0
        }, expected_status=201, module="Payroll")
        d12_id = d12.get("id") if isinstance(d12, dict) else 1
        await tester.request("GET", "/payroll/declarations/", expected_status=200, module="Payroll")
        await tester.request("PATCH", f"/payroll/declarations/{d12_id}/review", json_body={"status": "verified", "comments": "Investment proofs verified"}, expected_status=200, module="Payroll")

        # Salary Loan
        _, loan1 = await tester.request("POST", "/payroll/loans/", json_body={"amount": 50000.0, "reason": "Home relocation expense", "tenure_months": 5}, expected_status=201, module="Payroll")
        loan_id = loan1.get("id") if isinstance(loan1, dict) else 1
        await tester.request("GET", "/payroll/loans/", expected_status=200, module="Payroll")
        await tester.request("PATCH", f"/payroll/loans/{loan_id}/review", json_body={"status": "approved"}, expected_status=200, module="Payroll")

        # ─────────────────────────────────────────────────────────────
        # 7. EXPENSES & REIMBURSEMENTS
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 7. Expense Management & Reimbursements{Colors.END}")

        # Categories
        _, exp_cat = await tester.request("POST", "/expenses/categories/", json_body={"name": f"Client Dinner & Travel {timestamp_suffix}", "code": f"TRAVEL_{timestamp_suffix}", "max_limit": 25000.0}, expected_status=201, module="Expenses")
        exp_cat_id = exp_cat.get("id") if isinstance(exp_cat, dict) else 1
        await tester.request("GET", "/expenses/categories/", expected_status=200, module="Expenses")

        # Claims
        _, claim1 = await tester.request("POST", "/expenses/claims/", json_body={
            "category_id": exp_cat_id,
            "title": "Client Onboarding Dinner",
            "amount": 4200.0,
            "currency": "INR",
            "expense_date": today_str,
            "merchant": "Taj West End",
            "description": "Hosted dinner for enterprise client stakeholders"
        }, expected_status=201, module="Expenses")
        claim_id = claim1.get("id") if isinstance(claim1, dict) else 1

        await tester.request("GET", "/expenses/claims/", expected_status=200, module="Expenses")
        await tester.request("GET", "/expenses/claims/my", expected_status=200, module="Expenses")
        await tester.request("PATCH", f"/expenses/claims/{claim_id}/approve", expected_status=200, module="Expenses")
        await tester.request("PATCH", f"/expenses/claims/{claim_id}/reimburse", expected_status=200, module="Expenses")

        # Cash Advances
        _, adv1 = await tester.request("POST", "/expenses/advances/", json_body={"amount": 10000.0, "purpose": "International Conference Flight booking", "required_date": today_str}, expected_status=201, module="Expenses")
        adv_id = adv1.get("id") if isinstance(adv1, dict) else 1
        await tester.request("GET", "/expenses/advances/", expected_status=200, module="Expenses")
        await tester.request("PATCH", f"/expenses/advances/{adv_id}/review", json_body={"status": "approved", "notes": "Approved advance"}, expected_status=200, module="Expenses")

        # ─────────────────────────────────────────────────────────────
        # 8. PERFORMANCE MANAGEMENT SYSTEM (PMS) & OKRs
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 8. Performance Management (PMS) & OKRs{Colors.END}")

        # Goals & Key Results
        _, goal1 = await tester.request("POST", "/pms/goals/", json_body={
            "employee_id": emp_id,
            "title": "Scale Microservices to 99.99% Uptime",
            "category": "individual",
            "start_date": "2026-01-01",
            "due_date": "2026-12-31",
            "target_value": 100.0,
            "current_value": 45.0,
            "progress_percentage": 45.0,
            "key_results": [
                {"title": "Implement Redis distributed caching", "target_value": 100.0, "current_value": 80.0, "progress_percentage": 80.0},
                {"title": "Reduce P99 latency below 50ms", "target_value": 50.0, "current_value": 42.0, "metric_unit": "ms"}
            ]
        }, expected_status=201, module="PMS")
        goal_id = goal1.get("id") if isinstance(goal1, dict) else 1

        await tester.request("GET", "/pms/goals/", expected_status=200, module="PMS")
        await tester.request("GET", "/pms/goals/my", expected_status=200, module="PMS")
        await tester.request("PATCH", f"/pms/goals/{goal_id}", json_body={"progress_percentage": 65.0}, expected_status=200, module="PMS")

        # Review Cycles & Appraisals
        _, cycle1 = await tester.request("POST", "/pms/review-cycles/", json_body={
            "title": f"Annual Performance Review {curr_year} {timestamp_suffix}",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "review_type": "annual"
        }, expected_status=201, module="PMS")
        cycle_id = cycle1.get("id") if isinstance(cycle1, dict) else 1

        _, rev1 = await tester.request("POST", "/pms/reviews/", json_body={
            "cycle_id": cycle_id,
            "employee_id": emp_id,
            "reviewer_id": emp_id,
            "reviewer_type": "self"
        }, expected_status=201, module="PMS")
        rev_id = rev1.get("id") if isinstance(rev1, dict) else 1

        await tester.request("PATCH", f"/pms/reviews/{rev_id}/submit", json_body={
            "ratings_json": json.dumps({"Technical Skills": 5, "Team Collaboration": 5, "Delivery": 4.8}),
            "strengths": "Exceptional system design and speed of delivery",
            "areas_for_improvement": "More public tech talk presentations",
            "overall_score": 4.9
        }, expected_status=200, module="PMS")

        # 1-on-1 Meetings
        next_hour = (datetime.now() + timedelta(days=2)).isoformat()
        _, m1 = await tester.request("POST", "/pms/one-on-ones/", json_body={
            "employee_id": emp_id,
            "scheduled_at": next_hour,
            "duration_minutes": 45,
            "agenda": "Quarterly career roadmap and project feedback"
        }, expected_status=201, module="PMS")
        await tester.request("GET", "/pms/one-on-ones/", expected_status=200, module="PMS")

        # Peer Appreciation
        await tester.request("POST", "/pms/appreciations/", json_body={
            "recipient_id": emp_id,
            "badge_name": "Rockstar Problem Solver",
            "message": "Outstanding work on shipping the new HRMS backend features flawlessly!"
        }, expected_status=201, module="PMS")
        await tester.request("GET", "/pms/appreciations/", expected_status=200, module="PMS")

        # ─────────────────────────────────────────────────────────────
        # 9. RECRUITMENT & APPLICANT TRACKING SYSTEM (ATS)
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 9. Recruitment & Applicant Tracking (ATS){Colors.END}")

        # Job Postings
        _, job1 = await tester.request("POST", "/recruitment/jobs/", json_body={
            "title": f"Lead AI Engineer {timestamp_suffix}",
            "code": f"JOB-AI-{timestamp_suffix}",
            "department_id": dept_id,
            "location": "Bengaluru (Hybrid)",
            "employment_type": "full_time",
            "experience_level": "Senior",
            "min_salary": 2500000.0,
            "max_salary": 4500000.0,
            "description": "Architect and build next-gen AI agentic systems.",
            "requirements": "Strong Python, LLM architectures, distributed systems.",
            "status": "open"
        }, expected_status=201, module="Recruitment")
        job_id = job1.get("id") if isinstance(job1, dict) else 1
        await tester.request("GET", "/recruitment/jobs/", expected_status=200, module="Recruitment")

        # Candidates
        cand_email = f"candidate_{timestamp_suffix}@gmail.com"
        _, cand1 = await tester.request("POST", "/recruitment/candidates/", json_body={
            "job_id": job_id,
            "first_name": "David",
            "last_name": "Miller",
            "email": cand_email,
            "phone": "+919123456780",
            "current_company": "Uber",
            "current_ctc": 3000000.0,
            "expected_ctc": 4200000.0,
            "experience_years": 6.5,
            "status": "interviewing"
        }, expected_status=201, module="Recruitment")
        cand_id = cand1.get("id") if isinstance(cand1, dict) else 1

        await tester.request("GET", "/recruitment/candidates/", expected_status=200, module="Recruitment")
        await tester.request("PATCH", f"/recruitment/candidates/{cand_id}", json_body={"status": "shortlisted"}, expected_status=200, module="Recruitment")

        # Interviews
        interview_time = (datetime.now() + timedelta(days=1)).isoformat()
        _, int1 = await tester.request("POST", "/recruitment/interviews/", json_body={
            "candidate_id": cand_id,
            "interviewer_id": emp_id,
            "interview_type": "technical",
            "scheduled_time": interview_time,
            "duration_minutes": 60,
            "meeting_link": "https://meet.google.com/abc-defg-hij"
        }, expected_status=201, module="Recruitment")
        int_id = int1.get("id") if isinstance(int1, dict) else 1

        await tester.request("GET", "/recruitment/interviews/", expected_status=200, module="Recruitment")
        await tester.request("PATCH", f"/recruitment/interviews/{int_id}/feedback", json_body={"feedback": "Strong algorithmic foundations and great system design", "score": 9.5}, expected_status=200, module="Recruitment")

        # Job Offer
        _, off1 = await tester.request("POST", "/recruitment/offers/", json_body={
            "candidate_id": cand_id,
            "job_id": job_id,
            "offered_ctc": 4000000.0,
            "joining_date": (date.today() + timedelta(days=30)).isoformat(),
            "validity_date": (date.today() + timedelta(days=7)).isoformat()
        }, expected_status=201, module="Recruitment")
        off_id = off1.get("id") if isinstance(off1, dict) else 1
        await tester.request("PATCH", f"/recruitment/offers/{off_id}/status", json_body={"status": "accepted"}, expected_status=200, module="Recruitment")

        # Candidate to Employee Conversion
        await tester.request("POST", f"/recruitment/candidates/{cand_id}/convert-to-employee", json_body={
            "password": "Password@123",
            "department_id": dept_id,
            "job_title": "Lead AI Engineer"
        }, expected_status=200, module="Recruitment")

        # ─────────────────────────────────────────────────────────────
        # 10. HELPDESK & INTERNAL ENGAGEMENT
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 10. Helpdesk, Announcements & Pulse Surveys{Colors.END}")

        # Categories
        _, tcat1 = await tester.request("POST", "/helpdesk/categories/", json_body={"name": f"IT Hardware & Access {timestamp_suffix}", "description": "Laptop and network requests"}, expected_status=201, module="Helpdesk")
        tcat_id = tcat1.get("id") if isinstance(tcat1, dict) else 1
        await tester.request("GET", "/helpdesk/categories/", expected_status=200, module="Helpdesk")

        # Tickets
        _, tick1 = await tester.request("POST", "/helpdesk/tickets/", json_body={
            "category_id": tcat_id,
            "priority": "high",
            "subject": "Request for 4K External Monitor",
            "description": "Need dual monitor setup for frontend UI development."
        }, expected_status=201, module="Helpdesk")
        tick_id = tick1.get("id") if isinstance(tick1, dict) else 1

        await tester.request("GET", "/helpdesk/tickets/", expected_status=200, module="Helpdesk")
        await tester.request("GET", "/helpdesk/tickets/my", expected_status=200, module="Helpdesk")

        # Comments
        await tester.request("POST", f"/helpdesk/tickets/{tick_id}/comments/", json_body={"message": "IT team has approved the request. Dispatched from inventory."}, expected_status=201, module="Helpdesk")
        await tester.request("PATCH", f"/helpdesk/tickets/{tick_id}/resolve", json_body={"resolution_notes": "Monitor delivered and configured at desk."}, expected_status=200, module="Helpdesk")

        # Announcements
        await tester.request("POST", "/helpdesk/announcements/", json_body={
            "title": "Annual Company Hackathon 2026",
            "content": "Get ready for 48 hours of innovation and building game-changing products!",
            "priority": "high"
        }, expected_status=201, module="Helpdesk")
        await tester.request("GET", "/helpdesk/announcements/", expected_status=200, module="Helpdesk")

        # Pulse Surveys
        _, surv1 = await tester.request("POST", "/helpdesk/surveys/", json_body={
            "title": f"Q1 Employee Satisfaction Pulse {timestamp_suffix}",
            "description": "Tell us how we can make our workplace even better!",
            "questions_json": json.dumps([
                {"id": 1, "question": "How satisfied are you with the work culture?", "type": "rating_1_to_5"},
                {"id": 2, "question": "Do you feel supported by your manager?", "type": "yes_no"}
            ]),
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "is_anonymous": True
        }, expected_status=201, module="Helpdesk")
        surv_id = surv1.get("id") if isinstance(surv1, dict) else 1

        await tester.request("GET", "/helpdesk/surveys/", expected_status=200, module="Helpdesk")
        await tester.request("POST", "/helpdesk/surveys/responses/", json_body={
            "survey_id": surv_id,
            "answers_json": json.dumps({"1": 5, "2": "yes"})
        }, expected_status=201, module="Helpdesk")
        await tester.request("GET", f"/helpdesk/surveys/{surv_id}/responses", expected_status=200, module="Helpdesk")

        # ─────────────────────────────────────────────────────────────
        # 11. ASSET & INVENTORY MANAGEMENT
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 11. Asset & Inventory Management{Colors.END}")

        # Categories
        _, acat1 = await tester.request("POST", "/assets/categories/", json_body={"name": f"High-End Laptops {timestamp_suffix}", "description": "Apple & Dell Developer machines"}, expected_status=201, module="Assets")
        acat_id = acat1.get("id") if isinstance(acat1, dict) else 1
        await tester.request("GET", "/assets/categories/", expected_status=200, module="Assets")

        # Items
        _, asset1 = await tester.request("POST", "/assets/items/", json_body={
            "asset_code": f"AST-MAC-{timestamp_suffix}",
            "name": "Apple MacBook Pro M3 Max 16-inch",
            "category_id": acat_id,
            "serial_number": f"C02X{timestamp_suffix}99",
            "model_number": "A2991",
            "purchase_date": "2026-01-15",
            "purchase_cost": 349900.0,
            "status": "available"
        }, expected_status=201, module="Assets")
        asset_id = asset1.get("id") if isinstance(asset1, dict) else 1

        await tester.request("GET", "/assets/items/", expected_status=200, module="Assets")

        # Assignments & Return
        _, asgn1 = await tester.request("POST", "/assets/assignments/", json_body={
            "asset_id": asset_id,
            "employee_id": emp_id,
            "assigned_date": today_str,
            "condition_on_assignment": "Brand New Sealed",
            "notes": "Issued for primary development workload"
        }, expected_status=201, module="Assets")
        asgn_id = asgn1.get("id") if isinstance(asgn1, dict) else 1

        await tester.request("GET", "/assets/assignments/", expected_status=200, module="Assets")
        await tester.request("GET", "/assets/assignments/my", expected_status=200, module="Assets")
        await tester.request("PATCH", f"/assets/assignments/{asgn_id}/return", json_body={
            "return_date": today_str,
            "condition_on_return": "Good condition without scratches"
        }, expected_status=200, module="Assets")

        # ─────────────────────────────────────────────────────────────
        # 12. ANALYTICS & EXECUTIVE DASHBOARDS
        # ─────────────────────────────────────────────────────────────
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ 12. Executive Analytics & Workforce Reports{Colors.END}")

        await tester.request("GET", "/analytics/dashboard-summary", expected_status=200, module="Analytics")
        await tester.request("GET", "/analytics/headcount-trends", expected_status=200, module="Analytics")
        await tester.request("GET", "/analytics/attendance-overview", expected_status=200, module="Analytics")
        await tester.request("GET", "/analytics/leave-utilization", expected_status=200, module="Analytics")
        await tester.request("GET", "/analytics/payroll-cost-summary", expected_status=200, module="Analytics")
        await tester.request("GET", "/analytics/recruitment-funnel", expected_status=200, module="Analytics")

    # ─────────────────────────────────────────────────────────────
    # SUMMARY REPORT
    # ─────────────────────────────────────────────────────────────
    total_tests = len(tester.results)
    passed_tests = sum(1 for r in tester.results if r["passed"])
    failed_tests = total_tests - passed_tests

    print(f"\n{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════{Colors.END}")
    print(f"{Colors.BOLD}                      TEST SUITE EXECUTION SUMMARY                    {Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════{Colors.END}")
    print(f"  Total API Calls Executed: {Colors.BOLD}{total_tests}{Colors.END}")
    print(f"  Passed Operations:        {Colors.GREEN}{Colors.BOLD}{passed_tests}{Colors.END}")
    print(f"  Failed Operations:        {Colors.FAIL if failed_tests > 0 else Colors.GREEN}{Colors.BOLD}{failed_tests}{Colors.END}")
    print(f"  Success Rate:             {Colors.BOLD}{((passed_tests/total_tests)*100):.1f}%{Colors.END}")
    print(f"  Database Tenant Schema:   {Colors.CYAN}{company_name}{Colors.END}")
    print(f"  Admin User Credentials:   {Colors.CYAN}{admin_email} / {admin_password}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════{Colors.END}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test all HRMS APIs and seed dummy data")
    parser.add_argument("--url", type=str, default=None, help="Base URL of running HRMS FastAPI backend (e.g. http://localhost:8000)")
    args = parser.parse_args()

    asyncio.run(run_full_suite(args.url))
