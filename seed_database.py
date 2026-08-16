"""
HRMS PostgreSQL Database Auto-Seeder
====================================
Automatically populates the PostgreSQL database with a full set of realistic enterprise
data for all 13 modules whenever docker-compose starts or when executed standalone.

Default Demo Credentials Created:
  Company:   Nexus Tech
  Admin:     admin@nexustech.com    / Password@123  (Alex Vance)
  Employees: sarah.connor@nexustech.com / Password@123 (Sarah Connor)
             david.miller@nexustech.com / Password@123 (David Miller)
             elena.rostova@nexustech.com / Password@123 (Elena Rostova)
"""

import os
import sys
import asyncio
from datetime import datetime, date, timedelta
import json
import httpx

# Ensure app package is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app.db.session as db_session
from app.db.session import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


class DatabaseSeeder:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.token = None
        self.headers = {}

    def set_token(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post(self, endpoint: str, json_data: dict):
        resp = await self.client.post(f"/api/v1{endpoint}", json=json_data, headers=self.headers)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text

    async def patch(self, endpoint: str, json_data: dict = None):
        resp = await self.client.patch(f"/api/v1{endpoint}", json=json_data or {}, headers=self.headers)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text

    async def get(self, endpoint: str):
        resp = await self.client.get(f"/api/v1{endpoint}", headers=self.headers)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text


async def seed_all():
    print("=" * 70)
    print("🌱 HRMS Database Seeder Starting...")
    print("=" * 70)

    # 1. Check PostgreSQL or local fallback
    try:
        async with db_session.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"✓ Connected to PostgreSQL ({db_session.settings.POSTGRES_SERVER}:{db_session.settings.POSTGRES_PORT})")
    except Exception as e:
        print(f"⚠ PostgreSQL not reachable on {db_session.settings.POSTGRES_SERVER}:{db_session.settings.POSTGRES_PORT} ({e})")
        print("ℹ Initializing with local Async SQLite (test_hrms.db)...")
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///./test_hrms.db", echo=False, future=True)
        db_session.engine = sqlite_engine
        db_session.AsyncSessionLocal = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
        async with db_session.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Connected to local database.")

    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0) as client:
        seeder = DatabaseSeeder(client)

        company_name = "Nexus Tech"
        admin_email = "admin@nexustech.com"
        admin_password = "Password@123"

        # 1. Register Tenant / Company
        print("▶ 1. Seeding Tenant & Authentication...")
        code, reg_resp = await seeder.post("/tenants/register", {
            "company_name": company_name,
            "admin_email": admin_email,
            "admin_first_name": "Alex",
            "admin_last_name": "Vance",
            "admin_password": admin_password,
        })
        if code == 201:
            print("  ✓ Created Tenant: Nexus Tech")
        else:
            print("  ℹ Tenant Nexus Tech already exists or ready.")

        # Login as Admin
        code, login_resp = await seeder.post("/auth/login", {
            "company_name": company_name,
            "email": admin_email,
            "password": admin_password,
        })
        token = login_resp.get("access_token") if isinstance(login_resp, dict) else None
        if not token:
            print(f"  ⚠ Could not authenticate as {admin_email}. Response: {login_resp}")
            return
        seeder.set_token(token)
        admin_uid = login_resp.get("user_id", 1)
        print(f"  ✓ Authenticated as Admin ({admin_email})")

        # 2. Departments, Designations & Locations
        print("▶ 2. Seeding Core HR Structure...")
        _, dept_eng = await seeder.post("/core/departments/", {"name": "Engineering & Technology", "description": "Software, Cloud & AI Systems"})
        _, dept_hr = await seeder.post("/core/departments/", {"name": "People & Human Resources", "description": "People Ops, Culture & Recruitment"})
        _, dept_design = await seeder.post("/core/departments/", {"name": "Product & UI/UX Design", "description": "Product strategy and UI systems"})
        dept_eng_id = dept_eng.get("id", 1) if isinstance(dept_eng, dict) else 1
        dept_hr_id = dept_hr.get("id", 2) if isinstance(dept_hr, dict) else 2
        dept_design_id = dept_design.get("id", 3) if isinstance(dept_design, dict) else 3

        _, desig_lead = await seeder.post("/core/designations/", {"title": "Principal Staff Engineer", "department_id": dept_eng_id})
        _, desig_ai = await seeder.post("/core/designations/", {"title": "Lead AI Architect", "department_id": dept_eng_id})
        _, desig_designer = await seeder.post("/core/designations/", {"title": "Senior Product Designer", "department_id": dept_design_id})
        desig_lead_id = desig_lead.get("id", 1) if isinstance(desig_lead, dict) else 1
        desig_ai_id = desig_ai.get("id", 2) if isinstance(desig_ai, dict) else 2
        desig_designer_id = desig_designer.get("id", 3) if isinstance(desig_designer, dict) else 3

        _, loc_blr = await seeder.post("/core/locations/", {"name": "HQ - Bengaluru", "city": "Bengaluru", "state": "Karnataka", "address": "100ft Road, Indiranagar"})
        _, loc_hyd = await seeder.post("/core/locations/", {"name": "Hyderabad Campus", "city": "Hyderabad", "state": "Telangana", "address": "HITEC City"})
        loc_blr_id = loc_blr.get("id", 1) if isinstance(loc_blr, dict) else 1

        # 3. Create Employees
        _, emp_sarah = await seeder.post("/core/employees/", {
            "email": "sarah.connor@nexustech.com",
            "password": "Password@123",
            "first_name": "Sarah",
            "last_name": "Connor",
            "phone_number": "+919876543210",
            "job_title": "Principal Staff Engineer",
            "employee_code": "EMP-1001",
            "department_id": dept_eng_id,
            "designation_id": desig_lead_id,
            "work_location_id": loc_blr_id,
            "is_active": True,
        })
        emp_sarah_id = emp_sarah.get("id", 2) if isinstance(emp_sarah, dict) else 2

        _, emp_david = await seeder.post("/core/employees/", {
            "email": "david.miller@nexustech.com",
            "password": "Password@123",
            "first_name": "David",
            "last_name": "Miller",
            "phone_number": "+919123456780",
            "job_title": "Lead AI Architect",
            "employee_code": "EMP-1002",
            "department_id": dept_eng_id,
            "designation_id": desig_ai_id,
            "work_location_id": loc_blr_id,
            "is_active": True,
        })
        emp_david_id = emp_david.get("id", 3) if isinstance(emp_david, dict) else 3

        _, emp_elena = await seeder.post("/core/employees/", {
            "email": "elena.rostova@nexustech.com",
            "password": "Password@123",
            "first_name": "Elena",
            "last_name": "Rostova",
            "phone_number": "+919887766554",
            "job_title": "Senior Product Designer",
            "employee_code": "EMP-1003",
            "department_id": dept_design_id,
            "designation_id": desig_designer_id,
            "work_location_id": loc_blr_id,
            "is_active": True,
        })
        emp_elena_id = emp_elena.get("id", 4) if isinstance(emp_elena, dict) else 4
        print("  ✓ Seeded 4 Core Employees (Admin, Sarah, David, Elena)")

        # 4. Employee Profiles, Documents, Education, Experience
        print("▶ 3. Seeding Employee Profiles, Contacts & Education...")
        _, prof_admin = await seeder.post("/profiles/", {
            "user_id": admin_uid,
            "date_of_birth": "1990-01-01",
            "gender": "Male",
            "marital_status": "Single",
            "nationality": "Indian",
            "blood_group": "A+",
            "phone_number": "+919988776655",
            "personal_email": "alex.personal@gmail.com",
            "city": "Bengaluru",
            "state": "Karnataka",
            "employment_type": "Full Time",
            "date_of_joining": "2020-01-01",
            "skills": "Engineering Leadership, Cloud Systems, HR Operations",
        })
        _, prof_sarah = await seeder.post("/profiles/", {
            "user_id": emp_sarah_id,
            "date_of_birth": "1994-06-15",
            "gender": "Female",
            "marital_status": "Single",
            "nationality": "Indian",
            "blood_group": "O+",
            "phone_number": "+919876543210",
            "personal_email": "sarah.personal@gmail.com",
            "city": "Bengaluru",
            "state": "Karnataka",
            "employment_type": "Full Time",
            "date_of_joining": "2023-01-10",
            "skills": "React Native, FastAPI, PostgreSQL, Docker, Kubernetes",
        })
        sarah_prof_id = prof_sarah.get("id", 2) if isinstance(prof_sarah, dict) else 2
        await seeder.post(f"/profiles/{sarah_prof_id}/emergency-contacts", {
            "name": "John Connor",
            "relation_type": "Father",
            "phone_number": "+919876543299",
        })
        await seeder.post(f"/profiles/{sarah_prof_id}/education", {
            "degree": "B.Tech in Computer Science",
            "institution": "IIT Madras",
            "start_year": 2012,
            "end_year": 2016,
            "is_highest": True,
        })
        await seeder.post(f"/profiles/{sarah_prof_id}/experience", {
            "company_name": "Google",
            "job_title": "Software Engineer II",
            "start_date": "2016-07-01",
            "end_date": "2022-12-31",
            "is_current": False,
            "location": "Bengaluru",
        })

        # 5. Shifts, Attendance & Punches
        print("▶ 4. Seeding Shifts & Attendance Logs...")
        await seeder.post("/attendance/shifts/", {
            "name": "General Shift (9 AM - 6 PM)",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "grace_period_mins": 15,
            "is_default": True,
        })
        await seeder.post("/attendance/geofences/", {
            "name": "Bengaluru Main Campus",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "radius_meters": 300.0,
        })
        await seeder.post("/attendance/punch-in", {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "note": "Desk biometric clock-in",
        })
        today_str = date.today().isoformat()
        _, reg1 = await seeder.post("/attendance/regularizations/", {
            "date": today_str,
            "requested_punch_in": f"{today_str}T09:00:00Z",
            "requested_punch_out": f"{today_str}T18:00:00Z",
            "reason": "Biometric scanner sync delay",
        })
        await seeder.post("/attendance/overtime/", {
            "date": today_str,
            "overtime_hours": 2.5,
            "reason": "Production release deployment support",
        })

        # 6. Leave Types, Balances, Requests & Holidays
        print("▶ 5. Seeding Leaves & Holiday Calendar...")
        _, lt_cl = await seeder.post("/leave/types/", {"name": "Casual Leave", "code": "CL", "default_annual_quota": 12.0, "is_paid": True})
        _, lt_sl = await seeder.post("/leave/types/", {"name": "Sick Leave", "code": "SL", "default_annual_quota": 8.0, "is_paid": True})
        _, lt_el = await seeder.post("/leave/types/", {"name": "Earned Leave", "code": "EL", "default_annual_quota": 18.0, "is_paid": True})
        cl_id = lt_cl.get("id", 1) if isinstance(lt_cl, dict) else 1

        await seeder.post("/leave/balances/allocate-annual", {})
        next_week = (date.today() + timedelta(days=7)).isoformat()
        next_week_end = (date.today() + timedelta(days=8)).isoformat()
        _, lreq = await seeder.post("/leave/requests/", {
            "leave_type_id": cl_id,
            "start_date": next_week,
            "end_date": next_week_end,
            "days_count": 2.0,
            "reason": "Attending family wedding ceremony",
        })
        await seeder.post("/leave/holidays/", {"name": "Thanksgiving Holiday", "date": "2026-11-23", "description": "Public Holiday"})
        await seeder.post("/leave/holidays/", {"name": "Christmas Day", "date": "2026-12-25", "description": "National Holiday"})
        await seeder.post("/leave/holidays/", {"name": "New Year Holiday", "date": "2027-01-01", "description": "Annual Holiday"})

        # 7. Payroll, Salary Structures & Slips
        print("▶ 6. Seeding Payroll, Salary Components & Form 12BB...")
        await seeder.post("/payroll/components/", {"name": "Basic Salary", "code": "BASIC", "component_type": "earning", "calculation_type": "fixed", "is_taxable": True})
        await seeder.post("/payroll/components/", {"name": "House Rent Allowance", "code": "HRA", "component_type": "earning", "calculation_type": "percentage_of_basic", "default_value": 40.0})
        await seeder.post("/payroll/components/", {"name": "Provident Fund", "code": "PF", "component_type": "deduction", "calculation_type": "fixed", "is_statutory": True})
        _, struct = await seeder.post("/payroll/structures/", {"name": "Standard Tech Package", "description": "Software & Engineering CTC Structure"})
        struct_id = struct.get("id", 1) if isinstance(struct, dict) else 1

        await seeder.post("/payroll/employee-salaries/", {
            "employee_id": emp_sarah_id,
            "structure_id": struct_id,
            "annual_ctc": 1800000.0,
            "monthly_gross": 150000.0,
            "basic_salary": 60000.0,
            "effective_from": "2026-01-01",
            "bank_name": "HDFC Bank",
            "account_number": "50100234567890",
            "ifsc_code": "HDFC0001234",
            "pan_number": "ABCDE1234F",
            "tax_regime": "new",
        })
        curr_month = date.today().month
        curr_year = date.today().year
        await seeder.post("/payroll/runs/process", {"month": curr_month, "year": curr_year})
        await seeder.post("/payroll/declarations/", {
            "financial_year": "2026-2027",
            "section_80c": 150000.0,
            "section_80d": 25000.0,
            "hra_rent_paid": 240000.0,
        })
        await seeder.post("/payroll/loans/", {
            "amount": 50000.0,
            "reason": "Home relocation advance deposit",
            "tenure_months": 5,
        })

        # 8. Expense Management
        print("▶ 7. Seeding Expenses & Claims...")
        _, exp_cat1 = await seeder.post("/expenses/categories/", {"name": "Meals & Client Dining", "code": "MEALS", "max_limit": 15000.0})
        _, exp_cat2 = await seeder.post("/expenses/categories/", {"name": "Travel & Commute", "code": "TRAVEL", "max_limit": 30000.0})
        cat1_id = exp_cat1.get("id", 1) if isinstance(exp_cat1, dict) else 1

        await seeder.post("/expenses/claims/", {
            "category_id": cat1_id,
            "title": "Client Onboarding Dinner",
            "amount": 4200.0,
            "currency": "INR",
            "expense_date": today_str,
            "merchant": "Taj West End",
            "description": "Dinner with enterprise customer executive stakeholders",
        })
        await seeder.post("/expenses/advances/", {
            "amount": 10000.0,
            "purpose": "Tech summit flight and conference booking",
            "required_date": today_str,
        })

        # 9. PMS & Goals
        print("▶ 8. Seeding Performance Goals, OKRs & Kudos...")
        await seeder.post("/pms/goals/", {
            "employee_id": emp_sarah_id,
            "title": "Scale Microservices to 99.99% Uptime",
            "category": "Individual OKR",
            "start_date": "2026-01-01",
            "due_date": "2026-12-31",
            "target_value": 100.0,
            "current_value": 65.0,
            "progress_percentage": 65.0,
            "key_results": [
                {"title": "Implement Redis distributed caching", "target_value": 100.0, "current_value": 80.0, "progress_percentage": 80.0},
                {"title": "Reduce P99 latency below 50ms", "target_value": 50.0, "current_value": 42.0, "metric_unit": "ms"},
            ],
        })
        _, cycle = await seeder.post("/pms/review-cycles/", {
            "title": f"Annual Performance Review {curr_year}",
            "start_date": f"{curr_year}-01-01",
            "end_date": f"{curr_year}-12-31",
            "review_type": "annual",
        })
        next_meeting = (datetime.now() + timedelta(days=2)).isoformat()
        await seeder.post("/pms/one-on-ones/", {
            "employee_id": emp_sarah_id,
            "scheduled_at": next_meeting,
            "duration_minutes": 45,
            "agenda": "Quarterly career roadmap and project feedback",
        })
        await seeder.post("/pms/appreciations/", {
            "recipient_id": emp_sarah_id,
            "badge_name": "Rockstar Problem Solver",
            "message": "Outstanding work on shipping the new HRMS backend features flawlessly!",
        })

        # 10. Recruitment ATS
        print("▶ 9. Seeding Recruitment Jobs, Pipeline & Offers...")
        _, job = await seeder.post("/recruitment/jobs/", {
            "title": "Lead AI Architect",
            "code": "JOB-AI-2026",
            "department_id": dept_eng_id,
            "location": "Bengaluru (Hybrid)",
            "employment_type": "full_time",
            "experience_level": "Senior",
            "min_salary": 3000000.0,
            "max_salary": 5000000.0,
            "description": "Architect next-generation AI agentic systems and microservices.",
            "requirements": "Strong Python, LLMs, Distributed Systems, FastAPI",
            "status": "open",
        })
        job_id = job.get("id", 1) if isinstance(job, dict) else 1

        _, cand = await seeder.post("/recruitment/candidates/", {
            "job_id": job_id,
            "first_name": "Rohan",
            "last_name": "Gupta",
            "email": "rohan.gupta@gmail.com",
            "phone": "+919123456789",
            "current_company": "Zomato",
            "current_ctc": 3200000.0,
            "expected_ctc": 4500000.0,
            "experience_years": 7.0,
            "status": "interviewing",
        })
        cand_id = cand.get("id", 1) if isinstance(cand, dict) else 1
        interview_time = (datetime.now() + timedelta(days=1)).isoformat()
        await seeder.post("/recruitment/interviews/", {
            "candidate_id": cand_id,
            "interviewer_id": emp_sarah_id,
            "interview_type": "technical",
            "scheduled_time": interview_time,
            "duration_minutes": 60,
            "meeting_link": "https://meet.google.com/abc-defg-hij",
        })
        await seeder.post("/recruitment/offers/", {
            "candidate_id": cand_id,
            "job_id": job_id,
            "offered_ctc": 4200000.0,
            "joining_date": (date.today() + timedelta(days=30)).isoformat(),
            "validity_date": (date.today() + timedelta(days=7)).isoformat(),
        })

        # 11. Helpdesk & Surveys
        print("▶ 10. Seeding Helpdesk Tickets & Announcements...")
        _, tcat = await seeder.post("/helpdesk/categories/", {"name": "IT Hardware & Access", "description": "Laptops, monitors and network"})
        tcat_id = tcat.get("id", 1) if isinstance(tcat, dict) else 1
        _, tick = await seeder.post("/helpdesk/tickets/", {
            "category_id": tcat_id,
            "priority": "high",
            "subject": "Request for 4K External Monitor",
            "description": "Need dual monitor setup for UI development and design review.",
        })
        tick_id = tick.get("id", 1) if isinstance(tick, dict) else 1
        await seeder.post(f"/helpdesk/tickets/{tick_id}/comments/", {
            "message": "IT team has approved the request. Dispatched from inventory.",
        })
        await seeder.post("/helpdesk/announcements/", {
            "title": "Annual Company Hackathon 2026",
            "content": "Get ready for 48 hours of building groundbreaking products and AI agents!",
            "priority": "high",
        })
        _, surv = await seeder.post("/helpdesk/surveys/", {
            "title": "Q4 Employee Satisfaction & Culture Pulse",
            "description": "Tell us how we can make our workplace and culture even better!",
            "questions_json": json.dumps([
                {"id": 1, "question": "How satisfied are you with the hybrid culture?", "type": "rating_1_to_5"},
                {"id": 2, "question": "Do you feel supported by your manager?", "type": "yes_no"},
            ]),
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "is_anonymous": True,
        })

        # 12. Asset Management
        print("▶ 11. Seeding Hardware Assets & Inventory...")
        _, acat = await seeder.post("/assets/categories/", {"name": "High-Performance Laptops", "description": "Apple M3 & Dell machines"})
        acat_id = acat.get("id", 1) if isinstance(acat, dict) else 1
        _, asset1 = await seeder.post("/assets/items/", {
            "asset_code": "AST-MAC-991",
            "name": 'Apple MacBook Pro 16" (M3 Max / 36GB)',
            "category_id": acat_id,
            "serial_number": "C02XG1199",
            "model_number": "A2991",
            "purchase_date": "2026-01-15",
            "purchase_cost": 349900.0,
            "status": "assigned",
        })
        asset1_id = asset1.get("id", 1) if isinstance(asset1, dict) else 1
        await seeder.post("/assets/assignments/", {
            "asset_id": asset1_id,
            "employee_id": emp_sarah_id,
            "assigned_date": today_str,
            "condition_on_assignment": "Brand New Sealed",
            "notes": "Issued for software and design workload",
        })

        print("=" * 70)
        print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("  🏢 Company Tenant: Nexus Tech")
        print("  🔑 Admin Login:    admin@nexustech.com / Password@123")
        print("  👩 Employee Login: sarah.connor@nexustech.com / Password@123")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_all())
