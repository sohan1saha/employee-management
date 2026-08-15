# ⚡ StaffSync 360: Enterprise HRMS, Payroll & Audit Platform

> **Next-Generation Workforce Intelligence & Automated Payroll Management Platform**  
> Evolved from a foundational Python/SQL Employee Management core into a full-stack, enterprise-grade application with **FastAPI**, **SQLite / Cloud RDBMS**, **Role-Based Access Control (RBAC)**, **Dynamic PDF Payslip Generation**, and **Automated Audit Logging**.

---

## 🌟 Key Highlights & Features

1. **Foundational Core Preserved & Evolved:**
   * Retains the original field schema (`eid`, `ename`, `ecen`, `epos`, `esal`, `edoj`).
   * Retains the core CRUD functions: `addrec()`, `updrec()`, `disrec()`, `delrec()`.
   * **Dual Interface Mode:** Run via interactive terminal CLI (`python main.py --cli`) or launch the full web dashboard (`python main.py --web`).

2. **Automated Compensation & Payroll Engine:**
   * Automated salary breakdown: Basic (50%), HRA (20%), Special Allowance (30%), PF deductions (12% of basic), and progressive tax deductions.
   * **1-Click Monthly Payroll Generation** across all branch centers.
   * **Dynamic Corporate PDF Payslip Generation** built with ReportLab.

3. **Role-Based Access Control (RBAC):**
   * 👑 **Admin:** Full CRUD on employees, company-wide payroll processing, leave overrides, and security audit logs.
   * 👔 **Branch Manager:** Team oversight, center-specific metrics, and leave approvals.
   * 💻 **Employee:** Self-service profile, vacation/sick leave applications, and instant PDF payslip downloads.

4. **Zero-Trust Automated Audit Trail:**
   * Every modification to employee profiles, salaries, or statuses is automatically logged with before/after diffs, client IP, actor ID, and exact timestamp.

5. **Workforce Analytics Dashboard:**
   * Real-time KPI summaries: Total Active Headcount, Monthly Payroll Burn Rate, Operating Centers, and Pending Leaves.
   * Interactive distribution charts by center and job position.

6. **12-Factor Database Architecture:**
   * Uses **SQLAlchemy ORM** with SQLite out-of-the-box (`staffsync.db`).
   * Seamlessly connects to cloud **PostgreSQL (Supabase / Neon)** or **MySQL (TiDB Cloud)** simply by updating `DATABASE_URL` in `.env`.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
cd "E:\Projects\Employee Management"
pip install -r requirements.txt
```

### 2. Seed Initial Demo Data
Populates sample employees across Bangalore, Delhi, and Mumbai, along with default demo accounts:
```bash
python seed_data.py
```

**Demo Credentials (Employee ID & Password):**
* 👑 **Admin:** `Employee ID: 9924101` | `password: admin123`
* 👔 **Manager:** `Employee ID: 1023101` | `password: manager123`
* 💻 **Employee:** `Employee ID: 1025102` | `password: employee123`

---

## 👤 Author & Maintainer
Developed by **[Sohan Saha](https://github.com/sohan1saha)**

---

## 💻 Running the Application

### Option A: Launch Web Dashboard & REST API *(Default)*
```bash
python main.py
# or
python main.py --web
```
* 🌐 **Web Dashboard:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
* 📖 **Interactive Swagger Docs:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Option B: Run Interactive Terminal CLI Mode *(Original Script Evolution)*
```bash
python main.py --cli
```
Allows testing `addrec`, `disrec`, `updrec`, and `delrec` directly from your command-line interface.

---

## 🧪 Running Automated Tests
```bash
pytest tests/test_hrms.py -v
```

---

## 📂 Project Architecture

```text
E:\Projects\Employee Management\
├── app\
│   ├── api\                 # FastAPI REST API Routers
│   │   ├── auth_router.py
│   │   ├── employee_router.py
│   │   ├── payroll_router.py
│   │   ├── leave_router.py
│   │   ├── analytics_router.py
│   │   └── audit_router.py
│   ├── core\                # Core logic & database configuration
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── emp_mgmt_core.py # [Preserved original CRUD & CLI menu]
│   ├── models\              # SQLAlchemy ORM Data Models
│   │   ├── employee.py      # Evolved from em1 table
│   │   ├── user.py
│   │   ├── payroll.py
│   │   ├── leave.py
│   │   └── audit.py
│   ├── schemas\             # Pydantic validation schemas
│   ├── services\            # Business logic (Payroll math, PDF generator, Audit)
│   └── web\                 # Modern Glassmorphic Web Dashboard
│       ├── index.html
│       ├── css\style.css
│       └── js\
│           ├── api.js
│           └── app.js
├── main.py                  # Entry point (--cli and --web)
├── seed_data.py             # Database seeder
├── requirements.txt
└── .env
```
