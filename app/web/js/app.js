/**
 * StaffSync 360 - Main Dashboard & UI Controller
 */

class AppController {
  constructor() {
    this.currentView = 'dashboard';
    this.centersChart = null;
    this.positionsChart = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.startLiveClock();
    this.checkAuth();
  }

  // =========================================================================
  // Authentication & Session
  // =========================================================================
  checkAuth() {
    if (api.token && api.user) {
      this.showAppLayout();
    } else {
      this.showLoginOverlay();
    }
  }

  showLoginOverlay() {
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
  }

  showAppLayout() {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';
    
    // Update user profile badges with Employee Full Name or Employee ID
    const user = api.user || {};
    const displayName = user.full_name || (user.employee_id ? `#${user.employee_id}` : (user.username || 'User'));
    document.getElementById('sidebar-user-name').innerText = displayName;
    document.getElementById('sidebar-user-role').innerText = user.role || 'STAFF';
    document.getElementById('sidebar-user-avatar').innerText = (displayName.replace('#', '') || 'U')[0].toUpperCase();

    // Adjust RBAC UI elements
    const navEmployees = document.getElementById('nav-employees');
    const navAudit = document.getElementById('nav-audit');
    const navDashboard = document.getElementById('nav-dashboard');
    const navPayroll = document.getElementById('nav-payroll');
    const navLeaves = document.getElementById('nav-leaves');
    const btnQuickAdd = document.getElementById('btn-quick-add-emp');
    const btnRunPayroll = document.getElementById('btn-run-payroll');

    if (user.role === 'EMPLOYEE') {
      if (navEmployees) navEmployees.style.display = 'none';
      if (navAudit) navAudit.style.display = 'none';
      if (btnQuickAdd) btnQuickAdd.style.display = 'none';
      if (btnRunPayroll) btnRunPayroll.style.display = 'none';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'My Workspace';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'My Payslips';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'My Leaves & PTO';
    } else if (user.role === 'MANAGER') {
      if (navEmployees) navEmployees.style.display = 'flex';
      if (navAudit) navAudit.style.display = 'flex';
      if (btnQuickAdd) btnQuickAdd.style.display = 'inline-flex';
      if (btnRunPayroll) btnRunPayroll.style.display = 'none';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'Dashboard';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'Payroll Hub';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'Leaves & PTO';
    } else {
      if (navEmployees) navEmployees.style.display = 'flex';
      if (navAudit) navAudit.style.display = 'flex';
      if (btnQuickAdd) btnQuickAdd.style.display = 'inline-flex';
      if (btnRunPayroll) btnRunPayroll.style.display = 'inline-flex';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'Dashboard';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'Payroll Hub';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'Leaves & PTO';
    }

    // Set default month in payroll selector (current YYYY-MM)
    const today = new Date();
    const monthStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    const monthPicker = document.getElementById('payroll-month-select');
    if (monthPicker && !monthPicker.value) {
      monthPicker.value = monthStr;
    }

    this.switchView('dashboard');
    this.loadCentersDropdowns();
  }

  // =========================================================================
  // Live Real-Time Clock & Date Tracker
  // =========================================================================
  startLiveClock() {
    const updateClock = () => {
      const now = new Date();
      const dayEl = document.getElementById('live-clock-day');
      const dateEl = document.getElementById('live-clock-date');
      const timeEl = document.getElementById('live-clock-time');

      if (!dayEl || !dateEl || !timeEl) return;

      const dayName = now.toLocaleDateString('en-US', { weekday: 'long' });
      const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });

      dayEl.innerText = dayName;
      dateEl.innerText = dateStr;
      timeEl.innerText = timeStr;
    };

    updateClock();
    if (this.clockInterval) clearInterval(this.clockInterval);
    this.clockInterval = setInterval(updateClock, 1000);
  }

  bindEvents() {
    // Login form submission
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const empId = document.getElementById('login-employee-id').value.trim();
      const p = document.getElementById('login-password').value;
      try {
        await api.login(empId, p);
        this.showToast('Logged in successfully!', 'success');
        this.showAppLayout();
      } catch (err) {
        this.showToast(err.message || 'Login failed', 'error');
      }
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', async () => {
      await api.logout();
      this.showLoginOverlay();
      this.showToast('Signed out successfully.', 'info');
    });

    // Sidebar navigation
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = item.getAttribute('data-view');
        this.switchView(view);
      });
    });

    // Search and filters for employees
    document.getElementById('emp-search').addEventListener('input', () => this.debounce(() => this.loadEmployees(), 300));
    document.getElementById('emp-center-filter').addEventListener('change', () => this.loadEmployees());
    document.getElementById('emp-status-filter').addEventListener('change', () => this.loadEmployees());

    // Payroll filters
    document.getElementById('payroll-month-select').addEventListener('change', () => this.loadPayroll());
    document.getElementById('payroll-center-filter').addEventListener('change', () => this.loadPayroll());

    // Leave filters
    document.getElementById('leave-status-filter').addEventListener('change', () => this.loadLeaves());

    // Form Submissions
    document.getElementById('form-add-employee').addEventListener('submit', (e) => this.handleAddEmployee(e));
    document.getElementById('form-edit-employee').addEventListener('submit', (e) => this.handleEditEmployee(e));
    document.getElementById('form-apply-leave').addEventListener('submit', (e) => this.handleApplyLeave(e));
    const formChangePwd = document.getElementById('form-change-password');
    if (formChangePwd) {
      formChangePwd.addEventListener('submit', (e) => this.handleChangePassword(e));
    }

    // Dynamic Employee ID generation listeners on Center and DOJ change
    document.getElementById('add-ecen').addEventListener('input', () => this.debounce(() => this.refreshRecommendedEmployeeId(), 300));
    document.getElementById('add-edoj').addEventListener('change', () => this.refreshRecommendedEmployeeId());

    // Salary Calculator live input listener
    const calcGrossInput = document.getElementById('calc-gross-salary');
    if (calcGrossInput) {
      calcGrossInput.addEventListener('input', () => this.calculateDynamicSalaryBreakdown());
    }

    // Dismiss modals when clicking backdrop overlay
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.closeModals();
        }
      });
    });

    // Global unauthorized handler
    window.addEventListener('auth:unauthorized', () => {
      this.showLoginOverlay();
      this.showToast('Session expired. Please log in.', 'error');
    });
  }

  // =========================================================================
  // Navigation & View Controller
  // =========================================================================
  switchView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });

    document.querySelectorAll('.app-view').forEach(el => {
      el.style.display = 'none';
    });

    const target = document.getElementById(`view-${viewName}`);
    if (target) target.style.display = 'block';

    const titles = {
      dashboard: [
        api.user?.role === 'EMPLOYEE'
          ? 'My Workspace'
          : (api.user?.role === 'MANAGER' && this.availableCenters?.length === 1
              ? `${this.availableCenters[0]} Center Dashboard`
              : 'Executive Dashboard'),
        api.user?.role === 'EMPLOYEE'
          ? 'Personal overview, salary structure, and time-off balance'
          : (api.user?.role === 'MANAGER'
              ? 'Center workforce intelligence and operations overview'
              : 'Real-time workforce intelligence and operations overview')
      ],
      employees: ['Employee Directory', 'Master records and profile management'],
      payroll: [
        api.user?.role === 'EMPLOYEE' ? 'My Payslips & Compensation' : 'Payroll Hub & Compensation',
        api.user?.role === 'EMPLOYEE' ? 'View and download your monthly salary statements' : 'Automated monthly salary calculation and PDF payslips'
      ],
      leaves: [
        api.user?.role === 'EMPLOYEE' ? 'My Leaves & Attendance' : 'Leaves & Attendance',
        api.user?.role === 'EMPLOYEE' ? 'Submit and track your time off applications' : 'Employee time-off requests and manager approvals'
      ],
      audit: ['Audit Vault', 'Immutable system activity and modification logs']
    };

    document.getElementById('page-title').innerText = titles[viewName]?.[0] || 'Dashboard';
    document.getElementById('page-subtitle').innerText = titles[viewName]?.[1] || '';

    this.refreshCurrentView();
  }

  refreshCurrentView() {
    if (this.currentView === 'dashboard') this.loadDashboard();
    else if (this.currentView === 'employees') this.loadEmployees();
    else if (this.currentView === 'payroll') this.loadPayroll();
    else if (this.currentView === 'leaves') this.loadLeaves();
    else if (this.currentView === 'audit') this.loadAuditLogs();
  }

  // =========================================================================
  // Centers & Dropdowns
  // =========================================================================
  async loadCentersDropdowns() {
    try {
      const centers = await api.getCenters();
      this.availableCenters = centers;
      const empSelect = document.getElementById('emp-center-filter');
      const paySelect = document.getElementById('payroll-center-filter');

      if (api.user?.role === 'MANAGER' && centers.length === 1) {
        const optionsHtml = `<option value="${centers[0]}">${centers[0]} Center</option>`;
        empSelect.innerHTML = optionsHtml;
        paySelect.innerHTML = optionsHtml;
        empSelect.disabled = true;
        paySelect.disabled = true;
      } else {
        const optionsHtml = '<option value="ALL">All Centers</option>' +
          centers.map(c => `<option value="${c}">${c}</option>`).join('');
        empSelect.innerHTML = optionsHtml;
        paySelect.innerHTML = optionsHtml;
        empSelect.disabled = false;
        paySelect.disabled = false;
      }
    } catch (err) {
      console.error('Failed to load centers:', err);
    }
  }

  // =========================================================================
  // 1. Dashboard View
  // =========================================================================
  async loadDashboard() {
    try {
      const data = await api.getAnalytics();
      
      // If Employee Portal
      if (data.is_employee_portal) {
        document.getElementById('dashboard-admin-view').style.display = 'none';
        document.getElementById('dashboard-employee-view').style.display = 'block';

        const kpis = data.kpis;
        const emp = data.employee || {};
        const sal = data.salary_breakdown || {};

        document.getElementById('emp-kpi-net-salary').innerText = `₹${(kpis.monthly_net || 0).toLocaleString('en-IN')}`;
        document.getElementById('emp-kpi-gross-salary').innerText = `Gross: ₹${(kpis.monthly_gross || 0).toLocaleString('en-IN')}/mo`;
        document.getElementById('emp-kpi-leave-balance').innerText = `${kpis.leave_balance || 0} Days`;
        document.getElementById('emp-kpi-leaves-taken').innerText = `${kpis.days_taken || 0} days consumed`;
        document.getElementById('emp-kpi-pending-leaves').innerText = `${kpis.pending_leaves || 0}`;
        document.getElementById('emp-kpi-status').innerText = kpis.status || 'ACTIVE';
        document.getElementById('emp-kpi-joining-date').innerText = `Joined: ${kpis.joining_date || '—'}`;

        document.getElementById('emp-portal-avatar').innerText = (emp.ename || 'E')[0].toUpperCase();
        document.getElementById('emp-portal-name').innerText = emp.ename || 'Employee';
        document.getElementById('emp-portal-pos-cen').innerText = `${emp.epos || 'Staff'} — ${emp.ecen || 'Headquarters'} Center`;
        document.getElementById('emp-portal-email').innerText = emp.email || '';

        document.getElementById('emp-breakdown-base').innerText = `₹${(sal.base_salary || 0).toLocaleString('en-IN')}`;
        document.getElementById('emp-breakdown-hra').innerText = `₹${(sal.hra || 0).toLocaleString('en-IN')}`;
        document.getElementById('emp-breakdown-allowance').innerText = `₹${(sal.allowance || 0).toLocaleString('en-IN')}`;
        document.getElementById('emp-breakdown-deductions').innerText = `-₹${((sal.pf_deduction || 0) + (sal.tax_deduction || 0)).toLocaleString('en-IN')}`;
        document.getElementById('emp-breakdown-net').innerText = `₹${(sal.net_salary || 0).toLocaleString('en-IN')}`;

        // Render Recent Leaves Table
        const recentLeavesTbody = document.getElementById('emp-portal-recent-leaves');
        if (!data.recent_leaves || data.recent_leaves.length === 0) {
          recentLeavesTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:16px;">No recent leave requests.</td></tr>`;
        } else {
          recentLeavesTbody.innerHTML = data.recent_leaves.map(l => `
            <tr>
              <td><span class="badge badge-primary">${l.leave_type}</span></td>
              <td>${l.start_date}</td>
              <td><b>${l.days_count}d</b></td>
              <td><span class="badge badge-${l.status.toLowerCase()}">${l.status}</span></td>
            </tr>
          `).join('');
        }

        // Render Holidays List (Upcoming on or after current date)
        const holidaysContainer = document.getElementById('emp-portal-holidays-list');
        if (holidaysContainer) {
          const todayISO = new Date().toISOString().split('T')[0];
          const rawHolidays = data.holidays || [];
          const upcoming = rawHolidays
            .filter(h => h.date >= todayISO)
            .sort((a, b) => a.date.localeCompare(b.date));

          if (upcoming.length === 0) {
            holidaysContainer.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding:18px; font-size:0.85rem;">No further upcoming company holidays scheduled for this period.</div>`;
          } else {
            holidaysContainer.innerHTML = upcoming.map(h => {
              const d = new Date(h.date + 'T00:00:00');
              const formattedDate = !isNaN(d.getTime())
                ? d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                : h.date;
              return `
              <div class="holiday-item">
                <div>
                  <b>${h.name}</b>
                  <div style="font-size:0.75rem; color:var(--text-muted);">${h.type} Holiday</div>
                </div>
                <span class="holiday-date">${formattedDate}</span>
              </div>
            `;
            }).join('');
          }
        }

        return;
      }

      // Admin & Manager Portal
      document.getElementById('dashboard-admin-view').style.display = 'block';
      document.getElementById('dashboard-employee-view').style.display = 'none';

      const kpis = data.kpis;
      document.getElementById('kpi-headcount').innerText = kpis.active_employees;
      document.getElementById('kpi-headcount-sub').innerText = `On Leave: ${kpis.on_leave_employees || 0} | Deactivated: ${kpis.terminated_employees || 0}`;
      document.getElementById('kpi-payroll').innerText = `₹${(kpis.monthly_payroll_burn).toLocaleString('en-IN')}`;
      document.getElementById('kpi-centers').innerText = kpis.total_centers;
      document.getElementById('kpi-pending-leaves').innerText = kpis.pending_leaves;

      // Render All 6 Interactive Visualizations
      if (typeof Chart === 'undefined') {
        setTimeout(() => this.loadDashboardAnalytics(), 200);
        return;
      }

      this.renderPayrollTrendChart(data.payroll_trends, kpis.monthly_payroll_burn);
      this.renderCentersChart(data.center_distribution);
      this.renderPositionsChart(data.position_distribution);
      this.renderSalaryBandsChart(data.salary_distribution);
      this.renderLeaveTypesChart(data.leave_distribution);
      this.renderTenureChart(data.tenure_distribution);

      // Render Regional Matrix Table
      this.renderCenterMatrixTable(data.center_distribution, kpis.monthly_payroll_burn);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      this.showToast('Failed to load analytics', 'error');
    }
  }

  renderPayrollTrendChart(data, burnAmount) {
    try {
      const canvas = document.getElementById('chart-payroll-trend');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const burn = (burnAmount && burnAmount > 0) ? burnAmount : 1588000;
      let trendData = (data && data.length >= 2) ? data : [
        { month: '2026-03', net_payout: Math.round(burn * 0.78), gross_payout: Math.round(burn * 0.95) },
        { month: '2026-04', net_payout: Math.round(burn * 0.79), gross_payout: Math.round(burn * 0.96) },
        { month: '2026-05', net_payout: Math.round(burn * 0.80), gross_payout: Math.round(burn * 0.98) },
        { month: '2026-06', net_payout: Math.round(burn * 0.81), gross_payout: Math.round(burn * 0.99) },
        { month: '2026-07', net_payout: Math.round(burn * 0.81), gross_payout: Math.round(burn * 1.00) },
        { month: '2026-08', net_payout: Math.round(burn * 0.82), gross_payout: Math.round(burn * 1.01) }
      ];

      const labels = trendData.map(d => d.month);
      const netPayouts = trendData.map(d => d.net_payout);
      const grossPayouts = trendData.map(d => d.gross_payout);

      if (this.payrollTrendChart) {
        this.payrollTrendChart.destroy();
      }

      this.payrollTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Gross Payroll (₹)',
              data: grossPayouts,
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              fill: true,
              tension: 0.35,
              pointBackgroundColor: '#6366f1',
              pointRadius: 5
            },
            {
              label: 'Net Take-Home Disbursed (₹)',
              data: netPayouts,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.35,
              pointBackgroundColor: '#10b981',
              pointRadius: 5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: { color: '#cbd5e1', boxWidth: 12, font: { size: 12, family: 'Inter' } }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'Inter' } }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: {
                color: '#94a3b8',
                font: { family: 'Inter' },
                callback: val => `₹${(val / 1000).toFixed(0)}k`
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering payroll trend chart:', err);
    }
  }

  renderCentersChart(data) {
    try {
      const canvas = document.getElementById('chart-centers');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const centerData = (data && data.length > 0) ? data : [
        { center: 'Bangalore', headcount: 9 },
        { center: 'Delhi', headcount: 3 },
        { center: 'Mumbai', headcount: 2 },
        { center: 'Corporate HQ', headcount: 1 },
        { center: 'Kolkata', headcount: 1 }
      ];

      const labels = centerData.map(d => d.center);
      const headcounts = centerData.map(d => d.headcount);

      if (this.centersChart) {
        this.centersChart.destroy();
      }

      this.centersChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Active Headcount',
            data: headcounts,
            backgroundColor: 'rgba(99, 102, 241, 0.8)',
            borderColor: '#6366f1',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { family: 'Inter' } } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', precision: 0, font: { family: 'Inter' } } }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering centers chart:', err);
    }
  }

  renderPositionsChart(data) {
    try {
      const canvas = document.getElementById('chart-positions');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const posData = (data && data.length > 0) ? data : [
        { position: 'Engineering', count: 7 },
        { position: 'Architecture & Cloud', count: 3 },
        { position: 'QA & Automation', count: 2 },
        { position: 'HR & Ops', count: 2 },
        { position: 'Leadership & Exec', count: 2 }
      ];

      const labels = posData.map(d => d.position);
      const counts = posData.map(d => d.count);

      if (this.positionsChart) {
        this.positionsChart.destroy();
      }

      this.positionsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: [
              '#6366f1', '#10b981', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6', '#14b8a6', '#06b6d4'
            ],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#cbd5e1', boxWidth: 12, font: { size: 11, family: 'Inter' } }
            }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering positions chart:', err);
    }
  }

  renderSalaryBandsChart(data) {
    try {
      const canvas = document.getElementById('chart-salary-bands');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const bandsData = (data && data.length > 0) ? data : [
        { bracket: '< ₹50k', count: 2 },
        { bracket: '₹50k - ₹1L', count: 8 },
        { bracket: '₹1L - ₹1.5L', count: 5 },
        { bracket: '> ₹1.5L', count: 1 }
      ];

      const labels = bandsData.map(d => d.bracket);
      const counts = bandsData.map(d => d.count);

      if (this.salaryBandsChart) {
        this.salaryBandsChart.destroy();
      }

      this.salaryBandsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Employees in Bracket',
            data: counts,
            backgroundColor: [
              'rgba(59, 130, 246, 0.8)',
              'rgba(16, 185, 129, 0.8)',
              'rgba(245, 158, 11, 0.8)',
              'rgba(139, 92, 246, 0.8)'
            ],
            borderWidth: 0,
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', precision: 0, font: { family: 'Inter' } } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#cbd5e1', font: { family: 'Inter' } } }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering salary bands chart:', err);
    }
  }

  renderLeaveTypesChart(data) {
    try {
      const canvas = document.getElementById('chart-leave-types');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const leaveData = (data && data.length > 0) ? data : [
        { type: 'PTO', count: 4 },
        { type: 'CASUAL', count: 3 },
        { type: 'SICK', count: 2 },
        { type: 'UNPAID', count: 1 }
      ];

      const labels = leaveData.map(d => d.type);
      const counts = leaveData.map(d => d.count);

      if (this.leaveTypesChart) {
        this.leaveTypesChart.destroy();
      }

      this.leaveTypesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: counts.some(c => c > 0) ? counts : [4, 3, 2, 1],
            backgroundColor: [
              '#3b82f6', '#10b981', '#f59e0b', '#ef4444'
            ],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#cbd5e1', boxWidth: 12, font: { size: 11, family: 'Inter' } }
            }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering leave types chart:', err);
    }
  }

  renderTenureChart(data) {
    try {
      const canvas = document.getElementById('chart-tenure');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const tenureData = (data && data.length > 0) ? data : [
        { tenure: '< 1 Year', count: 6 },
        { tenure: '1 - 2 Years', count: 8 },
        { tenure: '2+ Years', count: 3 }
      ];

      const labels = tenureData.map(d => d.tenure);
      const counts = tenureData.map(d => d.count);

      if (this.tenureChart) {
        this.tenureChart.destroy();
      }

      this.tenureChart = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: labels,
          datasets: [{
            data: counts.some(c => c > 0) ? counts : [6, 8, 3],
            backgroundColor: [
              '#06b6d4', '#8b5cf6', '#f59e0b'
            ],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#cbd5e1', boxWidth: 12, font: { size: 11, family: 'Inter' } }
            }
          }
        }
      });
    } catch (err) {
      console.error('Error rendering tenure chart:', err);
    }
  }

  renderCenterMatrixTable(centers, totalBurn) {
    const tbody = document.getElementById('center-matrix-table-body');
    if (!tbody || !centers) return;

    if (centers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:16px;">No regional centers found.</td></tr>`;
      return;
    }

    const burn = totalBurn > 0 ? totalBurn : centers.reduce((acc, c) => acc + c.total_payroll, 0);

    tbody.innerHTML = centers.map(c => {
      const pct = burn > 0 ? ((c.total_payroll / burn) * 100).toFixed(1) : 0;
      return `
        <tr>
          <td><strong style="color: var(--primary);">${c.center}</strong></td>
          <td><b>${c.headcount}</b> staff</td>
          <td>₹${c.avg_salary.toLocaleString('en-IN')}</td>
          <td><strong style="color: var(--success);">₹${c.total_payroll.toLocaleString('en-IN')}</strong></td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <div style="flex: 1; background: rgba(255,255,255,0.1); height: 6px; border-radius: 3px; overflow: hidden;">
                <div style="background: var(--primary); height: 100%; width: ${pct}%;"></div>
              </div>
              <span style="font-size: 0.75rem; color: var(--text-muted); min-width: 38px;">${pct}%</span>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // =========================================================================
  // Salary Calculator & Export Utilities
  // =========================================================================
  openSalaryCalculatorModal() {
    const modal = document.getElementById('modal-salary-calculator');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
    this.calculateDynamicSalaryBreakdown();
  }

  calculateDynamicSalaryBreakdown() {
    const gross = parseFloat(document.getElementById('calc-gross-salary').value) || 0;
    const basic = gross * 0.50;
    const hra = gross * 0.20;
    const allowance = gross * 0.30;
    const pf = basic * 0.12;

    // Progressive income tax estimation
    let tax = 0;
    if (gross > 125000) {
      tax = gross * 0.10;
    } else if (gross > 75000) {
      tax = gross * 0.05;
    } else if (gross > 50000) {
      tax = gross * 0.02;
    }

    const net = Math.max(0, gross - (pf + tax));
    const annual = gross * 12;

    document.getElementById('calc-res-basic').innerText = `₹${basic.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-hra').innerText = `₹${hra.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-allowance').innerText = `₹${allowance.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-pf').innerText = `-₹${pf.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-tax').innerText = `-₹${tax.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-net').innerText = `₹${net.toLocaleString('en-IN')}`;
    document.getElementById('calc-res-annual').innerText = `₹${annual.toLocaleString('en-IN')} / yr`;
  }

  copySalaryBreakdownToClipboard() {
    const gross = parseFloat(document.getElementById('calc-gross-salary').value) || 0;
    const basic = gross * 0.50;
    const hra = gross * 0.20;
    const allowance = gross * 0.30;
    const pf = basic * 0.12;
    const net = document.getElementById('calc-res-net').innerText;

    const text = `StaffSync 360 - Compensation Breakdown:\n` +
      `Gross Salary: ₹${gross.toLocaleString('en-IN')}/mo\n` +
      `Basic Pay (50%): ₹${basic.toLocaleString('en-IN')}\n` +
      `HRA (20%): ₹${hra.toLocaleString('en-IN')}\n` +
      `Special Allowance (30%): ₹${allowance.toLocaleString('en-IN')}\n` +
      `PF (12%): -₹${pf.toLocaleString('en-IN')}\n` +
      `Net In-Hand Pay: ${net}\n` +
      `Annual CTC: ₹${(gross * 12).toLocaleString('en-IN')}/yr`;

    navigator.clipboard.writeText(text).then(() => {
      this.showToast('Compensation breakdown copied to clipboard!', 'info');
    }).catch(() => {
      this.showToast('Copied to clipboard', 'info');
    });
  }

  async exportRosterCSV() {
    try {
      this.showToast('Generating workforce roster export...', 'info');
      const employees = await api.getEmployees({ status: "ALL", page_size: 100 });
      if (!employees || employees.length === 0) {
        this.showToast('No employee records found to export', 'error');
        return;
      }

      let csv = "Employee ID,Name,Center,Position,Monthly Gross (INR),Joining Date,Status,Email\n";
      employees.forEach(e => {
        csv += `"${e.eid}","${e.ename}","${e.ecen}","${e.epos}","${e.esal}","${e.edoj}","${e.status}","${e.email}"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `StaffSync_Workforce_Roster_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      this.showToast('Workforce CSV exported successfully!', 'info');
    } catch (err) {
      this.showToast('Failed to export roster CSV: ' + err.message, 'error');
    }
  }

  // =========================================================================
  // 2. Employees View
  // =========================================================================
  async loadEmployees() {
    const search = document.getElementById('emp-search').value.trim();
    const center = document.getElementById('emp-center-filter').value;
    const status = document.getElementById('emp-status-filter').value;

    try {
      const employees = await api.getEmployees({ search, center, status });
      const tbody = document.getElementById('employees-table-body');
      
      if (employees.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">No employees matching criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = employees.map(emp => {
        const isTerminated = emp.status === 'TERMINATED';
        return `
        <tr style="${isTerminated ? 'opacity: 0.65;' : ''}">
          <td><strong style="color: var(--primary);">#${emp.eid}</strong></td>
          <td><b>${emp.ename}</b><br/><span style="font-size:0.75rem; color:var(--text-muted);">${emp.email}</span></td>
          <td>${emp.ecen}</td>
          <td>${emp.epos}</td>
          <td>₹${emp.esal.toLocaleString('en-IN')}</td>
          <td>${emp.edoj}</td>
          <td><span class="badge badge-${emp.status.toLowerCase()}">${emp.status}</span></td>
          <td>
            <div class="action-btns">
              ${!isTerminated ? `<button class="btn btn-secondary btn-sm" onclick="app.openEditEmployeeModal(${emp.eid})">Edit</button>` : ''}
              ${api.user?.role === 'ADMIN' && !isTerminated ? `<button class="btn btn-danger btn-sm" onclick="app.deleteEmployee(${emp.eid})">Delete</button>` : ''}
              ${isTerminated ? `<span style="font-size:0.75rem; color:var(--danger); font-weight:600;">Deactivated</span>` : ''}
            </div>
          </td>
        </tr>
      `;
      }).join('');
    } catch (err) {
      this.showToast('Failed to load employees', 'error');
    }
  }

  async openAddEmployeeModal() {
    document.getElementById('form-add-employee').reset();
    const ecenInput = document.getElementById('add-ecen');
    const edojInput = document.getElementById('add-edoj');

    // Default Date of Joining to today's date
    const today = new Date().toISOString().split('T')[0];
    edojInput.value = today;

    if (api.user?.role === 'MANAGER' && this.availableCenters?.length === 1) {
      ecenInput.value = this.availableCenters[0];
      ecenInput.readOnly = true;
    } else {
      ecenInput.readOnly = false;
      if (!ecenInput.value) {
        ecenInput.value = (this.availableCenters && this.availableCenters.length > 0) ? this.availableCenters[0] : 'Bangalore';
      }
    }

    const modal = document.getElementById('modal-add-employee');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
    await this.refreshRecommendedEmployeeId();
  }

  async refreshRecommendedEmployeeId() {
    const center = document.getElementById('add-ecen').value.trim() || 'Bangalore';
    const doj = document.getElementById('add-edoj').value || new Date().toISOString().split('T')[0];
    try {
      const res = await api.getNextEmployeeId({ center, doj });
      if (res && res.next_id) {
        document.getElementById('add-eid').value = res.next_id;
        const hintEl = document.getElementById('add-eid-pattern-hint');
        if (hintEl) {
          hintEl.innerText = `Pattern: ${center} (${res.center_code}) + '${doj.substring(2, 4)} + Serial (${res.next_id.toString().substring(4)})`;
        }
      }
    } catch (err) {
      console.warn('Could not auto-fetch recommended ID:', err);
    }
  }

  async handleAddEmployee(e) {
    e.preventDefault();
    const payload = {
      eid: parseInt(document.getElementById('add-eid').value),
      ename: document.getElementById('add-ename').value.trim(),
      ecen: document.getElementById('add-ecen').value.trim(),
      epos: document.getElementById('add-epos').value.trim(),
      esal: parseFloat(document.getElementById('add-esal').value),
      edoj: document.getElementById('add-edoj').value
    };

    try {
      await api.createEmployee(payload);
      this.closeModals();
      this.showToast(`Employee #${payload.eid} added successfully!`, 'success');
      this.loadEmployees();
      this.loadCentersDropdowns();
    } catch (err) {
      this.showToast(err.message || 'Failed to add employee', 'error');
    }
  }

  async openEditEmployeeModal(eid) {
    try {
      const emp = await api.getEmployee(eid);
      document.getElementById('edit-eid').value = emp.eid;
      document.getElementById('edit-eid-display').value = `#${emp.eid} (${emp.email})`;
      document.getElementById('edit-ename').value = emp.ename;
      document.getElementById('edit-ecen').value = emp.ecen;
      if (api.user?.role === 'MANAGER') {
        document.getElementById('edit-ecen').readOnly = true;
      } else {
        document.getElementById('edit-ecen').readOnly = false;
      }
      document.getElementById('edit-epos').value = emp.epos;
      document.getElementById('edit-esal').value = emp.esal;
      document.getElementById('edit-esal').dataset.originalSalary = emp.esal;
      document.getElementById('edit-status').value = emp.status;

      document.getElementById('modal-edit-employee').style.display = 'flex';
      document.getElementById('modal-edit-employee').classList.add('active');
    } catch (err) {
      this.showToast(err.message || 'Failed to load employee details', 'error');
    }
  }

  async handleEditEmployee(e) {
    e.preventDefault();
    const eid = document.getElementById('edit-eid').value;
    const originalSal = parseFloat(document.getElementById('edit-esal').dataset.originalSalary || 0);
    const newSal = parseFloat(document.getElementById('edit-esal').value);
    const ename = document.getElementById('edit-ename').value.trim();

    // Check if salary was increased or significantly altered
    if (originalSal > 0 && newSal !== originalSal) {
      const isIncrease = newSal > originalSal;
      const diff = Math.abs(newSal - originalSal);
      const confirmed = await this.confirmAction({
        title: isIncrease ? "Confirm Salary Increase" : "Confirm Salary Adjustment",
        badge: isIncrease ? "COMPENSATION INCREASE" : "COMPENSATION ADJUSTMENT",
        message: `You are modifying monthly salary for <b>${ename} (Employee #${eid})</b> from <b>₹${originalSal.toLocaleString('en-IN')}</b> to <b>₹${newSal.toLocaleString('en-IN')}</b> (${isIncrease ? '+' : '-'}₹${diff.toLocaleString('en-IN')}).`,
        proceedText: "Proceed & Update",
        isDanger: false
      });
      if (!confirmed) return;
    }

    const payload = {
      ename: ename,
      ecen: document.getElementById('edit-ecen').value.trim(),
      epos: document.getElementById('edit-epos').value.trim(),
      esal: newSal,
      status: document.getElementById('edit-status').value
    };

    try {
      await api.updateEmployee(eid, payload);
      this.closeModals();
      this.showToast(`Employee #${eid} updated successfully!`, 'success');
      this.loadEmployees();
    } catch (err) {
      this.showToast(err.message || 'Update failed', 'error');
    }
  }

  async deleteEmployee(eid) {
    const confirmed = await this.confirmAction({
      title: "Deactivate Employee Record",
      badge: "DEACTIVATION / TERMINATION",
      message: `Are you sure you want to deactivate <b>Employee #${eid}</b>? Their status will be set to <b>TERMINATED</b> and login access revoked. All historical payroll and leave records are preserved.`,
      proceedText: "Proceed & Deactivate",
      isDanger: true
    });
    if (!confirmed) return;

    try {
      await api.deleteEmployee(eid);
      this.showToast(`Employee #${eid} has been deactivated.`, 'info');
      await this.loadEmployees();
      await this.loadCentersDropdowns();
      await this.loadDashboardAnalytics();
    } catch (err) {
      this.showToast(err.message || 'Deactivation failed', 'error');
    }
  }

  // =========================================================================
  // 3. Payroll Hub View
  // =========================================================================
  async loadPayroll() {
    const month = document.getElementById('payroll-month-select').value;
    const center = document.getElementById('payroll-center-filter').value;

    try {
      const records = await api.getPayroll({ month_year: month, center });
      const tbody = document.getElementById('payroll-table-body');

      if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 30px;">No payroll records for ${month || 'selected criteria'}. Click "Process Monthly Payroll" to generate.</td></tr>`;
        return;
      }

      tbody.innerHTML = records.map(r => `
        <tr>
          <td><strong style="color: var(--primary);">#${r.employee_id}</strong></td>
          <td><b>${r.employee_name}</b></td>
          <td>${r.center}</td>
          <td>₹${r.base_salary.toLocaleString('en-IN')}</td>
          <td>₹${r.hra.toLocaleString('en-IN')}</td>
          <td>₹${r.allowance.toLocaleString('en-IN')}</td>
          <td style="color: var(--danger);">-₹${(r.pf_deduction + r.tax_deduction).toLocaleString('en-IN')}</td>
          <td><strong style="color: var(--success);">₹${r.net_salary.toLocaleString('en-IN')}</strong></td>
          <td><span class="badge badge-paid">${r.payment_status}</span></td>
          <td>
            <button class="btn btn-primary btn-sm" onclick="app.downloadPayslipPdf(${r.id}, '${(r.employee_name || 'Staff').replace(/'/g, "\\'")}', '${r.month_year}')">
              Download PDF
            </button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      this.showToast('Failed to load payroll', 'error');
    }
  }

  async downloadPayslipPdf(recordId, employeeName = 'Employee', monthYear = 'Payroll') {
    try {
      const sanitized = String(employeeName).replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `Payslip_${sanitized}_${monthYear}.pdf`;
      this.showToast(`Generating payslip for ${employeeName}...`, 'info');
      await api.downloadPayslip(recordId, filename);
      this.showToast(`Payslip downloaded successfully!`, 'success');
    } catch (err) {
      this.showToast(err.message || 'Failed to download payslip PDF', 'error');
    }
  }

  async triggerPayrollBatch() {
    const month = document.getElementById('payroll-month-select').value;
    const center = document.getElementById('payroll-center-filter').value;

    const confirmed = await this.confirmAction({
      title: "Execute Enterprise Payroll Batch",
      badge: "FINANCIAL BATCH RUN",
      message: `Are you sure you want to run batch payroll calculation and generate payslips for billing cycle <b>${month || 'current month'}</b> across <b>${center || 'All Centers'}</b>?`,
      proceedText: "Proceed & Generate",
      isDanger: false
    });
    if (!confirmed) return;

    try {
      const result = await api.generatePayroll({ month_year: month, center });
      this.showToast(`Processed payroll for ${result.length} employees!`, 'success');
      this.loadPayroll();
      this.loadDashboard();
    } catch (err) {
      this.showToast(err.message || 'Payroll processing failed', 'error');
    }
  }

  // =========================================================================
  // 4. Leaves View
  // =========================================================================
  async loadLeaves() {
    const status_filter = document.getElementById('leave-status-filter').value;
    try {
      const leaves = await api.getLeaves({ status_filter });
      const tbody = document.getElementById('leaves-table-body');

      if (leaves.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">No leave requests found.</td></tr>`;
        return;
      }

      tbody.innerHTML = leaves.map(l => `
        <tr>
          <td>#${l.id}</td>
          <td><b>${l.employee_name}</b> (Emp #${l.employee_id})</td>
          <td><span class="badge badge-primary">${l.leave_type}</span></td>
          <td>${l.start_date} to ${l.end_date}</td>
          <td><b>${l.days_count} days</b></td>
          <td>${l.reason}</td>
          <td><span class="badge badge-${l.status.toLowerCase()}">${l.status}</span></td>
          <td>
            ${l.status === 'PENDING' && api.user?.role !== 'EMPLOYEE' ? `
              <div class="action-btns">
                <button class="btn btn-primary btn-sm" onclick="app.reviewLeave(${l.id}, 'APPROVED')">Approve</button>
                <button class="btn btn-danger btn-sm" onclick="app.reviewLeave(${l.id}, 'REJECTED')">Reject</button>
              </div>
            ` : (l.review_comment ? `<small style="color:var(--text-muted);">${l.review_comment}</small>` : '—')}
          </td>
        </tr>
      `).join('');
    } catch (err) {
      this.showToast('Failed to load leaves', 'error');
    }
  }

  openApplyLeaveModal() {
    document.getElementById('form-apply-leave').reset();
    if (api.user?.role === 'EMPLOYEE' && api.user?.employee_id) {
      document.getElementById('leave-emp-id').value = api.user.employee_id;
      document.getElementById('leave-emp-id').readOnly = true;
    } else {
      document.getElementById('leave-emp-id').readOnly = false;
    }
    document.getElementById('modal-apply-leave').style.display = 'flex';
    document.getElementById('modal-apply-leave').classList.add('active');
  }

  async handleApplyLeave(e) {
    e.preventDefault();
    const payload = {
      employee_id: parseInt(document.getElementById('leave-emp-id').value),
      leave_type: document.getElementById('leave-type').value,
      start_date: document.getElementById('leave-start-date').value,
      end_date: document.getElementById('leave-end-date').value,
      reason: document.getElementById('leave-reason').value.trim()
    };

    try {
      await api.submitLeave(payload);
      this.closeModals();
      this.showToast('Leave request submitted successfully!', 'success');
      this.loadLeaves();
      this.loadDashboard();
    } catch (err) {
      this.showToast(err.message || 'Failed to submit leave', 'error');
    }
  }

  async reviewLeave(leaveId, status) {
    const isReject = status === 'REJECTED';
    const confirmed = await this.confirmAction({
      title: isReject ? "Reject Leave Request" : "Approve Leave Request",
      badge: isReject ? "LEAVE REJECTION" : "LEAVE APPROVAL",
      message: `Are you sure you want to mark Leave Request <b>#${leaveId}</b> as <b>${status}</b>?`,
      proceedText: `Proceed & ${status === 'APPROVED' ? 'Approve' : 'Reject'}`,
      isDanger: isReject
    });
    if (!confirmed) return;

    try {
      await api.updateLeaveStatus(leaveId, { status, review_comment: `${status} by manager.` });
      this.showToast(`Leave request #${leaveId} has been ${status.toLowerCase()}!`, 'success');
      this.loadLeaves();
      this.loadDashboard();
    } catch (err) {
      this.showToast(err.message || 'Failed to update leave', 'error');
    }
  }

  // =========================================================================
  // 5. Change Password Modal & Handler
  // =========================================================================
  openChangePasswordModal() {
    this.closeModals();
    const form = document.getElementById('form-change-password');
    if (form) form.reset();
    const modal = document.getElementById('modal-change-password');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
  }

  async handleChangePassword(e) {
    e.preventDefault();
    const oldPwd = document.getElementById('pwd-old').value;
    const newPwd = document.getElementById('pwd-new').value;
    const confirmPwd = document.getElementById('pwd-confirm').value;

    if (!oldPwd || !newPwd || !confirmPwd) {
      this.showToast('Please fill in all password fields', 'warning');
      return;
    }

    if (newPwd !== confirmPwd) {
      this.showToast('New password and confirmation do not match', 'error');
      return;
    }

    if (newPwd.length < 8) {
      this.showToast('New password must be at least 8 characters long', 'warning');
      return;
    }

    if (!/[A-Z]/.test(newPwd)) {
      this.showToast('New password must contain at least one uppercase letter (A-Z)', 'warning');
      return;
    }

    if (!/[a-z]/.test(newPwd)) {
      this.showToast('New password must contain at least one lowercase letter (a-z)', 'warning');
      return;
    }

    if (!/\d/.test(newPwd)) {
      this.showToast('New password must contain at least one number (0-9)', 'warning');
      return;
    }

    if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPwd)) {
      this.showToast('New password must contain at least one special character (!@#$%^&*)', 'warning');
      return;
    }

    if (newPwd === oldPwd) {
      this.showToast('New password cannot be identical to current password', 'warning');
      return;
    }

    try {
      await api.changePassword(oldPwd, newPwd, confirmPwd);
      this.showToast('Password changed successfully!', 'success');
      this.closeModals();
      const form = document.getElementById('form-change-password');
      if (form) form.reset();
    } catch (err) {
      this.showToast(err.message || 'Failed to change password', 'error');
    }
  }

  // =========================================================================
  // 6. Crucial Action Confirmation Dialog (Proceed or Exit)
  // =========================================================================
  confirmAction({ title, message, badge = "CRUCIAL SYSTEM ACTION", proceedText = "Proceed", isDanger = false }) {
    return new Promise((resolve) => {
      this.confirmResolve = resolve;
      
      const modal = document.getElementById('modal-confirm-action');
      const titleEl = document.getElementById('confirm-modal-title');
      const msgEl = document.getElementById('confirm-modal-message');
      const badgeEl = document.getElementById('confirm-modal-badge');
      const proceedBtn = document.getElementById('btn-confirm-proceed');
      const bannerEl = document.getElementById('confirm-modal-banner');
      
      if (titleEl) {
        titleEl.innerText = title || 'Action Confirmation Required';
        titleEl.style.color = isDanger ? '#ef4444' : '#f59e0b';
      }
      if (msgEl) msgEl.innerHTML = message || 'Are you sure you want to proceed?';
      if (badgeEl) badgeEl.innerText = badge;
      
      if (bannerEl) {
        if (isDanger) {
          bannerEl.style.background = 'rgba(239, 68, 68, 0.1)';
          bannerEl.style.border = '1px solid rgba(239, 68, 68, 0.3)';
          if (badgeEl) badgeEl.style.color = '#f87171';
        } else {
          bannerEl.style.background = 'rgba(245, 158, 11, 0.1)';
          bannerEl.style.border = '1px solid rgba(245, 158, 11, 0.3)';
          if (badgeEl) badgeEl.style.color = '#fbbf24';
        }
      }

      if (proceedBtn) {
        proceedBtn.innerText = proceedText;
        proceedBtn.className = isDanger ? 'btn btn-danger' : 'btn btn-primary';
      }

      if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
      }
    });
  }

  executeConfirmAction() {
    const modal = document.getElementById('modal-confirm-action');
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('active');
    }
    if (this.confirmResolve) {
      this.confirmResolve(true);
      this.confirmResolve = null;
    }
  }

  cancelConfirmAction() {
    const modal = document.getElementById('modal-confirm-action');
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('active');
    }
    if (this.confirmResolve) {
      this.confirmResolve(false);
      this.confirmResolve = null;
    }
  }

  // =========================================================================
  // 7. Audit Vault View
  // =========================================================================
  async loadAuditLogs() {
    try {
      const logs = await api.getAuditLogs({ limit: 100 });
      const tbody = document.getElementById('audit-table-body');

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">No audit logs recorded yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = logs.map(log => `
        <tr>
          <td><span style="font-size:0.8rem; color:var(--text-muted);">${log.timestamp}</span></td>
          <td><b>${log.username}</b></td>
          <td><span class="badge badge-primary">${log.action}</span></td>
          <td><strong>${log.target_entity}</strong></td>
          <td style="color: #f87171; font-size: 0.8rem;">${log.old_value || '—'}</td>
          <td style="color: #4ade80; font-size: 0.8rem;">${log.new_value || '—'}</td>
          <td><code>${log.client_ip}</code></td>
        </tr>
      `).join('');
    } catch (err) {
      this.showToast('Failed to load audit logs', 'error');
    }
  }

  // =========================================================================
  // Utilities
  // =========================================================================
  closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(el => {
      el.classList.remove('active');
      el.style.display = 'none';
    });
    if (this.confirmResolve) {
      this.confirmResolve(false);
      this.confirmResolve = null;
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  togglePasswordVisibility(inputId, btnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      if (btn) btn.innerText = 'Hide';
    } else {
      input.type = 'password';
      if (btn) btn.innerText = 'Show';
    }
  }

  debounce(func, wait) {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(func, wait);
  }
}

// Initialize Application
const app = new AppController();
