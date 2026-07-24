# Architecture Design: Keka HRMS Clone

Building a comprehensive HRMS like Keka requires a robust, scalable, and secure architecture. Given your chosen tech stack (React for Frontend, FastAPI for Backend), here is a detailed architectural blueprint to guide your development.

## 1. High-Level Architecture

For a project of this scale, starting with a **Modular Monolith** is recommended over full microservices. It keeps initial development fast while allowing easy transition to microservices later as specific modules (like Payroll or ATS) scale.

*   **Client Layer:** Web App (React), Mobile Apps (React Native - optional future scope).
*   **API Gateway / Load Balancer:** Nginx or cloud-native load balancer (AWS ALB) to route traffic and handle SSL termination.
*   **Backend Application Layer:** FastAPI application structured into distinct domains/modules.
*   **Data Layer:** Primary Relational Database (PostgreSQL), Caching Layer (Redis), Object Storage (AWS S3) for documents.

---

## 2. Frontend Architecture (React)

The frontend needs to handle complex states, permissions, and dynamic forms.

*   **Core Framework:** React 18+ (Consider Next.js for better routing, SSR, and SEO if public pages like job postings are needed, otherwise Vite for a pure SPA dashboard).
*   **State Management:**
    *   **Server State:** React Query (TanStack Query) - Crucial for caching API responses (e.g., employee lists, leave balances) and handling mutations.
    *   **Client/UI State:** Zustand or React Context for global UI state (sidebar toggle, current user profile, active theme).
*   **UI Library/Design System:**
    *   Material-UI (MUI), Ant Design, or Tailwind CSS + shadcn/ui. Keka has a very clean, professional enterprise look.
*   **Form Management & Validation:** React Hook Form + Zod (for type-safe schema validation matching FastAPI).
*   **Routing:** React Router v6.
*   **Component Structure (Feature-Sliced Design):**
    ```
    src/
    ├── features/          # Grouped by business domain
    │   ├── auth/
    │   ├── employee-core/
    │   ├── payroll/
    │   ├── attendance/
    │   └── recruitment/
    ├── shared/            # Common UI components, hooks, utils
    │   ├── ui/            # Buttons, Tables, Modals
    │   └── api/           # Axios instance, generic API functions
    ├── app/               # Global styles, providers, router config
    └── pages/             # Page level components composing features
    ```

---

## 3. Backend Architecture (FastAPI)

FastAPI is excellent for this due to its speed, asynchronous capabilities, and automatic Swagger/OpenAPI documentation.

*   **Architecture Pattern:** Domain-Driven Design (DDD) principles applied to a Modular Monolith.
*   **Web Framework:** FastAPI (Python 3.10+).
*   **ORM:** SQLAlchemy (v2.0) with async capabilities (asyncpg).
*   **Data Validation:** Pydantic (built into FastAPI).
*   **Background Tasks / Message Queue:** Celery + Redis (or RabbitMQ). Essential for heavy tasks:
    *   Processing monthly payroll for thousands of employees.
    *   Sending bulk emails (payslips, announcements).
    *   Generating heavy compliance reports.
*   **Authentication & Authorization:**
    *   **Auth:** JWT (JSON Web Tokens) or session-based cookies. OAuth2 for SSO (Google, Microsoft).
    *   **RBAC (Role-Based Access Control):** Granular permissions are critical. Every endpoint must check if the user has `read`, `write`, or `admin` access to specific resources (e.g., "Can view own payslip", "Can edit subordinate's leave").
*   **Project Structure:**
    ```python
    app/
    ├── core/              # Config, Security, Database session, Celery setup
    ├── api/               # API Routers (v1)
    │   ├── v1/
    │   │   ├── auth.py
    │   │   ├── employees.py
    │   │   ├── payroll.py
    ├── modules/           # Business Logic (The "Domains")
    │   ├── employee/      # Models, Schemas, CRUD, Services
    │   ├── attendance/
    │   ├── payroll/
    │   └── leave/
    ├── migrations/        # Alembic for DB migrations
    └── main.py            # FastAPI application entry point
    ```

---

## 4. Database Architecture

A relational database is mandatory for an HRMS to ensure ACID properties, especially for payroll and financial data.

*   **Primary DB:** PostgreSQL.
*   **Caching:** Redis (Cache API responses, store user sessions, Celery broker).
*   **File Storage:** AWS S3, Google Cloud Storage, or MinIO (for local dev). Store profile pictures, resumes, offer letters, and tax documents here, saving only the URL in the database.

### Key Database Schemas (Simplified)

1.  **Core Entity:** `users` / `employees` (ID, Name, Email, Role_ID, Manager_ID, Department_ID).
2.  **Organization:** `departments`, `locations`, `designations`.
3.  **Attendance:** `attendance_logs` (Employee_ID, Timestamp, Type [In/Out], Location), `shifts`.
4.  **Leaves:** `leave_types`, `leave_balances`, `leave_requests` (Status: Pending, Approved, Rejected).
5.  **Payroll:** `salary_structures`, `allowances`, `deductions`, `payslips` (Generated monthly records).
6.  **Auth:** `roles`, `permissions`, `role_permissions_mapping`.

---

## 5. Mapping Keka Features to Your Tech Stack

Here is how you implement specific Keka features:

### A. Core HR & Employee Data
*   **Implementation:** Standard CRUD operations in FastAPI. Use SQLAlchemy relationships to link employees to departments, managers, and locations.
*   **Documents:** Upload files via FastAPI to S3. Store the S3 URI in a `documents` table linked to the `employee_id`.

### B. Attendance & Leave
*   **Geo-fencing/Selfie Attendance:** Frontend (React Native for mobile, or browser Geolocation API) captures coordinates and photo. FastAPI verifies if coordinates fall within the allowed polygon (using PostGIS extension in PostgreSQL for spatial queries).
*   **Leave Accrual Engine:** A Celery cron job that runs daily or monthly to calculate and add leave balances based on company policy.

### C. Payroll & Compliance
*   **The Calculation Engine:** This is the most complex backend piece. Create a dedicated Python service (`PayrollCalculator`) that takes an employee's salary structure, attendance data, and tax declarations, and calculates Gross, Deductions (PF, Taxes), and Net Pay.
*   **Payslip Generation:** Use a Python library like `ReportLab` or `WeasyPrint` (HTML to PDF) in a Celery background task to generate PDF payslips and upload them to S3.

### D. Talent Management (ATS & Performance)
*   **ATS:** Kanban board in React (using libraries like `@hello-pangea/dnd`) for tracking candidates through stages.
*   **Performance:** Form builders in React allowing HR to create custom review templates. Store these dynamic structures in PostgreSQL using `JSONB` columns for flexibility.

### E. Automation & Workflows
*   **Implementation:** Implement a finite state machine (FSM) in Python. When a leave is requested, its state is `PENDING`. It triggers a notification (via WebSockets or email) to the Manager. Upon approval, state changes to `APPROVED`, triggering another event to update the leave balance.

---

## 6. Infrastructure & Deployment (DevOps)

*   **Containerization:** Dockerize both React (served via Nginx) and FastAPI applications.
*   **Orchestration:** Docker Compose for local development. Kubernetes (EKS/GKE) or AWS ECS for production.
*   **CI/CD:** GitHub Actions or GitLab CI to automate testing, building Docker images, and deploying.
*   **Monitoring:** Prometheus + Grafana for server metrics. Sentry for capturing error logs from both React and FastAPI.

## First Steps to Begin:
1.  **Define the Database Schema:** Start by drawing an Entity-Relationship (ER) diagram for the Core HR module (Employees, Departments, Roles).
2.  **Setup Boilerplate:** Initialize the FastAPI project with SQLAlchemy and Alembic. Initialize the React project with Vite, React Query, and Tailwind.
3.  **Implement Auth & RBAC:** Build the login system and the foundational Role-Based Access Control before building any business features.
