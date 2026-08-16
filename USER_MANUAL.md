# 📖 Apex HRMS — Enterprise User & Administrator Handbook

Welcome to the **Apex HRMS** user manual. This document guides Administrators, Regional Managers, and Employees through the complete feature suite of the platform.

---

## 📑 Table of Contents
1. [Platform Access & Security Roles](#1-platform-access--security-roles)
2. [Global Command Palette (`Ctrl + K`)](#2-global-command-palette-ctrl--k)
3. [Daily Attendance, Shifts & Break Tracking](#3-daily-attendance-shifts--break-tracking)
4. [Statutory Indian Payroll Engine](#4-statutory-indian-payroll-engine)
5. [360 Performance Appraisals](#5-360-performance-appraisals)
6. [Employee Compliance Document Vault](#6-employee-compliance-document-vault)
7. [Leaves & Time-Off Management](#7-leaves--time-off-management)
8. [Workforce Analytics & Reporting](#8-workforce-analytics--reporting)

---

## 1. Platform Access & Security Roles

Apex HRMS uses a **3-Tier Role-Based Access Control (RBAC)** architecture:

* 👑 **Corporate Admin (e.g. Eleanor Vance `#9924101`):**
  - Enterprise-wide authority across all branches.
  - Can register employees, execute monthly payroll runs, disburse funds, and inspect security audit logs.
  - Reviews and approves leave applications submitted by Regional Managers.
* 👔 **Regional Manager (e.g. Sara Chen `#1023101`):**
  - Scoped to designated regional branch (e.g. Bangalore, Delhi, Mumbai, Kolkata).
  - Can author performance appraisals, approve team member leaves, upload staff compliance certificates, and monitor live branch duty rosters.
  - Personal leave requests are routed to Corporate Admin (self-approval is prevented).
* 💻 **Employee (e.g. Jordan Rivera `#1025102`):**
  - Privacy-isolated self-service workspace.
  - Can clock in/out, take breaks, download PDF payslips, submit leave applications, acknowledge performance reviews, and manage personal vault documents.

---

## 2. Global Command Palette (`Ctrl + K`)

Press **`Ctrl + K`** (Windows/Linux) or **`Cmd + K`** (macOS) anywhere in the application to activate the spotlight launcher:
* **Quick Navigation:** Jump instantly to any tab (*"Attendance"*, *"Payroll"*, *"Appraisals"*, *"Documents"*).
* **Instant Actions:** One-click shortcuts to *Clock In*, *Take Break*, *Apply for Leave*, or *Open Salary Calculator*.
* **Keyboard Control:** Use `↑` / `↓` arrow keys to highlight items and `Enter` to execute. Press `Esc` to dismiss.

---

## 3. Daily Attendance, Shifts & Break Tracking

### Shift Standards & Punctuality
* **Scheduled Shift:** Standard working hours are `09:00 AM – 06:00 PM IST` (8.0 Hours Target).
* **Punctuality Evaluation:**
  - **Early Arrival:** Clocked in before `09:00 AM IST` $\to$ `🟢 Early Arrival`.
  - **On-Time / Punctual:** Clocked in between `09:00 AM – 09:15 AM IST` $\to$ `🟢 On-Time`.
  - **Late Arrival:** Clocked in after `09:15 AM IST` $\to$ `🟡 Late by X mins` (exact late minutes recorded in attendance logs).

### Taking & Resuming Breaks (`☕ Take Break` / `▶ Resume Work`)
1. Click **`☕ Take Break`** when pausing work. Status updates to `☕ ON BREAK` with an active break stopwatch.
2. Click **`▶ Resume Work`** to resume shift duties. Total break duration is accumulated in seconds and automatically deducted from gross shift time on clock-out.

### Overtime Tracking
* When **Net Active Working Hours** exceed **8.0 Hours**, the stopwatch highlights with a `🔥 Overtime` badge.

---

## 4. Statutory Indian Payroll Engine

### Compensation Formula Breakdown
Salaries are calculated using statutory Indian payroll standards:
$$\text{Basic Salary} = 50\% \times \text{Gross Salary}$$
$$\text{House Rent Allowance (HRA)} = 20\% \times \text{Gross Salary}$$
$$\text{Special Allowance} = 30\% \times \text{Gross Salary}$$
$$\text{Employee PF} = 12\% \times \text{Basic Salary}$$
$$\text{Net Salary} = \text{Gross} - \text{PF Deduction} - \text{Income Tax}$$

### Payroll State Transitions
$$\text{DRAFT} \longrightarrow \text{CALCULATED} \longrightarrow \text{APPROVED} \longrightarrow \text{PAID}$$
* **Immutability Lock:** Once marked as `PAID`, records cannot be modified or deleted.
* **PDF Payslips:** Download high-resolution corporate payslips with native Rupee (`₹`) glyphs.

---

## 5. 360 Performance Appraisals

1. **Manager Authors Review:** Rates performance (1–5 Stars), evaluates goal alignment, notes key strengths, and gives feedback.
2. **Employee Notification:** Employee receives an in-app alert.
3. **Review Acknowledgement:** Employee opens appraisal, reads feedback, adds comments, and clicks **Acknowledge Review**.

---

## 6. Employee Compliance Document Vault

* **Supported Formats:** PDF, PNG, JPG, JPEG, DOCX (Max 10MB).
* **Security Inspection:** Every upload undergoes file extension and **Magic Byte header validation** to prevent spoofed/polyglot files.
* **Categories:** National ID / Passport, Employment Contracts, Degree Certificates, Tax Forms.

---

## 7. Leaves & Time-Off Management

* **Leave Types:** `SICK`, `CASUAL`, `PTO`, `UNPAID`.
* **Approval Routing:** Staff requests $\to$ Regional Manager. Manager requests $\to$ Corporate Admin.
* **Self-Approval Guard:** System enforces zero self-approval.

---

## 8. Workforce Analytics & Reporting

* **Interactive Charts:** Headcount distribution by center, salary burn, and designation allocation.
* **CSV Export:** One-click workforce roster CSV export (`ApexHRMS_Workforce_Roster_[Date].csv`).
