/**
 * Apex HRMS - Enterprise Main Dashboard & UI Controller
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
    this.startNotificationPolling();
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
    const empInput = document.getElementById('login-employee-id');
    const pwdInput = document.getElementById('login-password');
    if (empInput) empInput.value = '';
    if (pwdInput) pwdInput.value = '';
    if (empInput) empInput.focus();
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
    const navAttendance = document.getElementById('nav-attendance');
    const navPerformance = document.getElementById('nav-performance');
    const navDocuments = document.getElementById('nav-documents');
    const btnQuickAdd = document.getElementById('btn-quick-add-emp');
    const btnRunPayroll = document.getElementById('btn-run-payroll');
    const btnOpenAddReview = document.getElementById('btn-open-add-review');
    const docTargetWrap = document.getElementById('doc-target-emp-wrap');

    if (user.role === 'EMPLOYEE') {
      if (navEmployees) navEmployees.style.display = 'none';
      if (navAudit) navAudit.style.display = 'none';
      if (btnQuickAdd) btnQuickAdd.style.display = 'none';
      if (btnRunPayroll) btnRunPayroll.style.display = 'none';
      if (btnOpenAddReview) btnOpenAddReview.style.display = 'none';
      if (docTargetWrap) docTargetWrap.style.display = 'none';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'My Workspace';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'My Payslips';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'My Leaves & PTO';
      if (navAttendance) navAttendance.querySelector('span').innerText = 'My Attendance';
      if (navPerformance) navPerformance.querySelector('span').innerText = 'My Appraisals';
      if (navDocuments) navDocuments.querySelector('span').innerText = 'My Documents';
    } else if (user.role === 'MANAGER') {
      if (navEmployees) navEmployees.style.display = 'flex';
      if (navAudit) navAudit.style.display = 'flex';
      if (btnQuickAdd) btnQuickAdd.style.display = 'inline-flex';
      if (btnRunPayroll) btnRunPayroll.style.display = 'none';
      if (btnOpenAddReview) btnOpenAddReview.style.display = 'inline-flex';
      if (docTargetWrap) docTargetWrap.style.display = 'block';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'Dashboard';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'Payroll Hub';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'Leaves & PTO';
      if (navAttendance) navAttendance.querySelector('span').innerText = 'Attendance';
      if (navPerformance) navPerformance.querySelector('span').innerText = 'Performance';
      if (navDocuments) navDocuments.querySelector('span').innerText = 'Document Vault';
    } else {
      if (navEmployees) navEmployees.style.display = 'flex';
      if (navAudit) navAudit.style.display = 'flex';
      if (btnQuickAdd) btnQuickAdd.style.display = 'inline-flex';
      if (btnRunPayroll) btnRunPayroll.style.display = 'inline-flex';
      if (btnOpenAddReview) btnOpenAddReview.style.display = 'inline-flex';
      if (docTargetWrap) docTargetWrap.style.display = 'block';
      if (navDashboard) navDashboard.querySelector('span').innerText = 'Dashboard';
      if (navPayroll) navPayroll.querySelector('span').innerText = 'Payroll Hub';
      if (navLeaves) navLeaves.querySelector('span').innerText = 'Leaves & PTO';
      if (navAttendance) navAttendance.querySelector('span').innerText = 'Attendance';
      if (navPerformance) navPerformance.querySelector('span').innerText = 'Performance';
      if (navDocuments) navDocuments.querySelector('span').innerText = 'Document Vault';
    }

    // Set default month in payroll selector (current YYYY-MM)
    const today = new Date();
    const monthStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    const monthPicker = document.getElementById('payroll-month-select');
    if (monthPicker && !monthPicker.value) {
      monthPicker.value = monthStr;
    }

    const currentHash = window.location.hash.replace('#', '');
    const validViews = ['dashboard', 'attendance', 'employees', 'payroll', 'leaves', 'performance', 'documents', 'audit'];
    const initialView = validViews.includes(currentHash) ? currentHash : 'dashboard';
    this.switchView(initialView, true);
    this.loadCentersDropdowns();
    this.loadNotifications();
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
      const empInput = document.getElementById('login-employee-id');
      const pwdInput = document.getElementById('login-password');
      const empId = empInput.value.trim();
      const p = pwdInput.value;
      try {
        await api.login(empId, p);
        this.showToast('Logged in successfully!', 'success');
        empInput.value = '';
        pwdInput.value = '';
        this.showAppLayout();
      } catch (err) {
        this.showToast(err.message || 'Login failed. Invalid credentials.', 'error');
        // Clear previous entries from boxes on failed attempt and refocus
        empInput.value = '';
        pwdInput.value = '';
        empInput.focus();
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
    const formAddPerf = document.getElementById('form-add-performance');
    if (formAddPerf) {
      formAddPerf.addEventListener('submit', (e) => this.handleAddPerformanceReview(e));
    }
    const formAckPerf = document.getElementById('form-ack-performance');
    if (formAckPerf) {
      formAckPerf.addEventListener('submit', (e) => this.handleAckPerformanceReview(e));
    }
    const formUploadDoc = document.getElementById('form-upload-document');
    if (formUploadDoc) {
      formUploadDoc.addEventListener('submit', (e) => this.handleUploadDocument(e));
    }

    // Dynamic Employee ID generation listeners on Center and DOJ change
    document.getElementById('add-ecen').addEventListener('input', () => this.debounce(() => this.refreshRecommendedEmployeeId(), 300));
    document.getElementById('add-edoj').addEventListener('change', () => this.refreshRecommendedEmployeeId());

    // Salary Calculator live input listener
    const calcGrossInput = document.getElementById('calc-gross-salary');
    if (calcGrossInput) {
      calcGrossInput.addEventListener('input', () => this.calculateDynamicSalaryBreakdown());
    }

    // Close notification dropdown when clicking outside
    document.addEventListener('click', (e) => {
      const notifWrap = document.getElementById('notification-bell-wrap');
      const notifDrop = document.getElementById('notification-dropdown');
      if (notifWrap && notifDrop && !notifWrap.contains(e.target)) {
        notifDrop.style.display = 'none';
      }
    });

    // Dismiss modals when clicking backdrop overlay
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.closeModals();
        }
      });
    });

    // Global Spotlight Command Palette (Ctrl+K / Cmd+K)
    const handleGlobalKeydown = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K' || e.code === 'KeyK')) {
        e.preventDefault();
        e.stopPropagation();
        this.toggleCommandPalette();
      } else if (e.key === 'Escape') {
        this.closeCommandPalette();
        this.closeModals();
      }
    };
    window.addEventListener('keydown', handleGlobalKeydown, true);
    document.addEventListener('keydown', handleGlobalKeydown, true);

    // URL Hash Navigation Listener
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '');
      const validViews = ['dashboard', 'attendance', 'employees', 'payroll', 'leaves', 'performance', 'documents', 'audit'];
      if (validViews.includes(hash) && this.currentView !== hash) {
        this.switchView(hash, false);
      }
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
  switchView(viewName, updateHash = true) {
    this.currentView = viewName;
    if (updateHash && window.location.hash !== `#${viewName}`) {
      history.pushState(null, '', `#${viewName}`);
    }

    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });

    document.querySelectorAll('.app-view').forEach(el => {
      el.style.display = 'none';
    });

    const target = document.getElementById(`view-${viewName}`);
    if (target) target.style.display = 'block';

    const titles = {
      dashboard: api.user?.role === 'EMPLOYEE'
        ? 'My Workspace'
        : (api.user?.role === 'MANAGER' && this.availableCenters?.length === 1
            ? `${this.availableCenters[0]} Dashboard`
            : 'Dashboard'),
      attendance: api.user?.role === 'EMPLOYEE' ? 'My Attendance' : 'Attendance',
      employees: 'Employee Directory',
      payroll: api.user?.role === 'EMPLOYEE' ? 'My Payslips' : 'Payroll Hub',
      leaves: api.user?.role === 'EMPLOYEE' ? 'My Leaves & PTO' : 'Leaves & PTO',
      performance: api.user?.role === 'EMPLOYEE' ? 'My Performance' : 'Performance & Appraisals',
      documents: api.user?.role === 'EMPLOYEE' ? 'My Documents' : 'Document Vault',
      audit: api.user?.role === 'MANAGER' && this.availableCenters?.length === 1
        ? `${this.availableCenters[0]} Center Audit Trail`
        : 'Audit Trail'
    };

    const titleEl = document.getElementById('page-title');
    if (titleEl) titleEl.innerText = titles[viewName] || 'Dashboard';

    this.closeMobileSidebar();
    this.refreshCurrentView();
  }

  toggleMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar) return;
    sidebar.classList.toggle('mobile-open');
    if (backdrop) {
      if (sidebar.classList.contains('mobile-open')) {
        backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
      } else {
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
      }
    }
  }

  closeMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }

  refreshCurrentView() {
    if (this.currentView === 'dashboard') this.loadDashboard();
    else if (this.currentView === 'attendance') this.loadAttendanceData();
    else if (this.currentView === 'employees') this.loadEmployees();
    else if (this.currentView === 'payroll') this.loadPayroll();
    else if (this.currentView === 'leaves') this.loadLeaves();
    else if (this.currentView === 'performance') this.loadPerformanceReviews();
    else if (this.currentView === 'documents') this.loadDocuments();
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
      const attSelect = document.getElementById('att-center-filter');

      if (api.user?.role === 'EMPLOYEE') {
        if (attSelect) attSelect.style.display = 'none';
      } else if (api.user?.role === 'MANAGER' && centers.length === 1) {
        const optionsHtml = `<option value="${centers[0]}">${centers[0]} Center</option>`;
        if (empSelect) { empSelect.innerHTML = optionsHtml; empSelect.disabled = true; }
        if (paySelect) { paySelect.innerHTML = optionsHtml; paySelect.disabled = true; }
        if (attSelect) { attSelect.innerHTML = optionsHtml; attSelect.disabled = true; attSelect.style.display = 'inline-block'; }
      } else {
        const optionsHtml = '<option value="ALL">All Centers</option>' +
          centers.map(c => `<option value="${c}">${c}</option>`).join('');
        if (empSelect) { empSelect.innerHTML = optionsHtml; empSelect.disabled = false; }
        if (paySelect) { paySelect.innerHTML = optionsHtml; paySelect.disabled = false; }
        if (attSelect) { attSelect.innerHTML = optionsHtml; attSelect.disabled = false; attSelect.style.display = 'inline-block'; }
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

        // Live attendance tracking card update
        this.loadAttendanceData();
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
        setTimeout(() => this.loadDashboard(), 200);
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

      // Always sync personal attendance tracker for Admin/Manager
      await this.loadAttendanceData();
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

    const text = `Apex HRMS - Compensation Breakdown:\n` +
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
      link.setAttribute('download', `ApexHRMS_Workforce_Roster_${new Date().toISOString().split('T')[0]}.csv`);
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
    const tbody = document.getElementById('employees-table-body');
    if (tbody) tbody.innerHTML = this.renderSkeletonRows(8, 5);

    const search = document.getElementById('emp-search')?.value.trim() || '';
    const center = document.getElementById('emp-center-filter')?.value || '';
    const status = document.getElementById('emp-status-filter')?.value || '';

    try {
      const employees = await api.getEmployees({ search, center, status });
      if (!tbody) return;
      
      if (employees.length === 0) {
        tbody.innerHTML = this.renderEmptyState(
          '👥',
          'No Employees Found',
          search || center ? 'No staff records matched the specified search and filter criteria.' : 'No active employee records exist in this branch directory.',
          api.user?.role === 'ADMIN' ? '<button class="btn btn-primary btn-sm" onclick="app.openAddEmployeeModal()" style="margin-top: 10px;">+ Add New Employee</button>' : ''
        );
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
      if (tbody) tbody.innerHTML = this.renderErrorState('Failed to retrieve employee roster from server.', 'app.loadEmployees()');
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
    const systemRole = document.getElementById('add-system-role')?.value || 'EMPLOYEE';
    const initPwd = document.getElementById('add-initial-password')?.value.trim() || undefined;

    const payload = {
      eid: parseInt(document.getElementById('add-eid').value),
      ename: document.getElementById('add-ename').value.trim(),
      ecen: document.getElementById('add-ecen').value.trim(),
      epos: document.getElementById('add-epos').value.trim(),
      esal: parseFloat(document.getElementById('add-esal').value),
      edoj: document.getElementById('add-edoj').value,
      system_role: systemRole,
      initial_password: initPwd
    };

    try {
      await api.createEmployee(payload);
      this.closeModals();
      const roleMsg = systemRole === 'MANAGER' ? ` as ${payload.ecen} Branch Manager (Authority Granted)` : '';
      this.showToast(`Employee #${payload.eid} created successfully${roleMsg}!`, 'success');
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
        const roleWrap = document.getElementById('edit-system-role-wrap');
        if (roleWrap) roleWrap.style.display = 'none';
      } else {
        document.getElementById('edit-ecen').readOnly = false;
        const roleWrap = document.getElementById('edit-system-role-wrap');
        if (roleWrap) roleWrap.style.display = 'block';
      }
      document.getElementById('edit-epos').value = emp.epos;
      document.getElementById('edit-esal').value = emp.esal;
      document.getElementById('edit-esal').dataset.originalSalary = emp.esal;
      document.getElementById('edit-status').value = emp.status;

      const roleSelect = document.getElementById('edit-system-role');
      if (roleSelect) {
        roleSelect.value = emp.epos && emp.epos.toLowerCase().includes('manager') ? 'MANAGER' : 'EMPLOYEE';
      }

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
      status: document.getElementById('edit-status').value,
      system_role: document.getElementById('edit-system-role')?.value
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
      await this.loadDashboard();
    } catch (err) {
      this.showToast(err.message || 'Deactivation failed', 'error');
    }
  }

  // =========================================================================
  // 3. Payroll Hub View
  // =========================================================================
  async loadPayroll() {
    const tbody = document.getElementById('payroll-table-body');
    if (tbody) tbody.innerHTML = this.renderSkeletonRows(10, 5);

    const month = document.getElementById('payroll-month-select')?.value || '';
    const center = document.getElementById('payroll-center-filter')?.value || '';

    try {
      const records = await api.getPayroll({ month_year: month, center });
      if (!tbody) return;

      if (records.length === 0) {
        tbody.innerHTML = this.renderEmptyState(
          '💰',
          'No Payroll Records Found',
          `No generated payroll batch found for cycle ${month || 'current month'}.`,
          api.user?.role !== 'EMPLOYEE' ? `<button class="btn btn-primary btn-sm" onclick="app.triggerPayrollBatch()" style="margin-top: 10px;">⚡ Run Payroll Batch</button>` : ''
        );
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
      if (tbody) tbody.innerHTML = this.renderErrorState('Failed to retrieve payroll records from server.', 'app.loadPayroll()');
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
    const tbody = document.getElementById('leaves-table-body');
    if (tbody) tbody.innerHTML = this.renderSkeletonRows(8, 5);

    const status_filter = document.getElementById('leave-status-filter')?.value || '';
    
    // Dynamically configure action buttons for role
    const btnMyLeave = document.getElementById('btn-apply-my-leave');
    const btnStaffLeave = document.getElementById('btn-apply-staff-leave');
    if (api.user?.role === 'MANAGER') {
      if (btnMyLeave) btnMyLeave.style.display = 'inline-flex';
      if (btnStaffLeave) {
        btnStaffLeave.style.display = 'inline-flex';
        btnStaffLeave.innerText = '+ Request for Staff';
      }
    } else if (api.user?.role === 'EMPLOYEE') {
      if (btnMyLeave) btnMyLeave.style.display = 'none';
      if (btnStaffLeave) {
        btnStaffLeave.style.display = 'inline-flex';
        btnStaffLeave.innerText = '+ Request Time Off';
      }
    } else {
      if (btnMyLeave) btnMyLeave.style.display = 'none';
      if (btnStaffLeave) {
        btnStaffLeave.style.display = 'inline-flex';
        btnStaffLeave.innerText = '+ Apply Leave on Behalf';
      }
    }

    try {
      const leaves = await api.getLeaves({ status_filter });
      if (!tbody) return;

      if (leaves.length === 0) {
        tbody.innerHTML = this.renderEmptyState(
          '📅',
          'No Time-Off Requests',
          status_filter ? `No leave requests matching status '${status_filter}'.` : 'No submitted PTO applications exist in this period.',
          `<button class="btn btn-primary btn-sm" onclick="app.openApplyLeaveModal()" style="margin-top: 10px;">+ Request Time Off</button>`
        );
        return;
      }

      tbody.innerHTML = leaves.map(l => {
        const isSelf = l.employee_id === api.user?.employee_id;
        const isManagerApplicant = l.position && l.position.toLowerCase().includes('manager');
        let actionCell = '—';

        if (l.status === 'PENDING') {
          if (isSelf) {
            actionCell = `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; font-size:0.75rem;">⏳ Awaiting Admin Approval</span>`;
          } else if (api.user?.role === 'ADMIN') {
            actionCell = `
              <div class="action-btns">
                <button class="btn btn-primary btn-sm" onclick="app.reviewLeave(${l.id}, 'APPROVED')">Approve</button>
                <button class="btn btn-danger btn-sm" onclick="app.reviewLeave(${l.id}, 'REJECTED')">Reject</button>
              </div>
            `;
          } else if (api.user?.role === 'MANAGER') {
            if (isManagerApplicant) {
              actionCell = `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; font-size:0.75rem;">⏳ Awaiting Admin Approval</span>`;
            } else {
              actionCell = `
                <div class="action-btns">
                  <button class="btn btn-primary btn-sm" onclick="app.reviewLeave(${l.id}, 'APPROVED')">Approve</button>
                  <button class="btn btn-danger btn-sm" onclick="app.reviewLeave(${l.id}, 'REJECTED')">Reject</button>
                </div>
              `;
            }
          } else {
            actionCell = `<span class="badge badge-pending">PENDING</span>`;
          }
        } else {
          actionCell = l.review_comment ? `<small style="color:var(--text-muted);">${l.review_comment}</small>` : (l.reviewed_by ? `<small style="color:var(--text-muted);">Reviewed by ${l.reviewed_by}</small>` : '—');
        }

        return `
          <tr>
            <td>#${l.id}</td>
            <td><b>${l.employee_name}</b> <small style="color:var(--text-muted);">(#${l.employee_id})</small><br><small style="color:var(--text-muted);">${l.position || 'Staff'} • ${l.center || ''}</small></td>
            <td><span class="badge badge-primary">${l.leave_type}</span></td>
            <td>${l.start_date} to ${l.end_date}</td>
            <td><b>${l.days_count} days</b></td>
            <td>${l.reason}</td>
            <td><span class="badge badge-${l.status.toLowerCase()}">${l.status}</span></td>
            <td>${actionCell}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      if (tbody) tbody.innerHTML = this.renderErrorState('Failed to retrieve leave requests from server.', 'app.loadLeaves()');
      this.showToast('Failed to load leaves', 'error');
    }
  }

  openApplyLeaveModal(forSelf = false) {
    document.getElementById('form-apply-leave').reset();
    const empIdInput = document.getElementById('leave-emp-id');
    if (empIdInput) {
      if (forSelf || (api.user?.role === 'EMPLOYEE' && api.user?.employee_id)) {
        empIdInput.value = api.user?.employee_id || '';
        empIdInput.readOnly = true;
      } else {
        empIdInput.value = '';
        empIdInput.readOnly = false;
      }
    }
    const modal = document.getElementById('modal-apply-leave');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
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

  promptCrucialAction(title, message, proceedText = "Proceed", cancelText = "Exit") {
    return this.confirmAction({ title, message, proceedText });
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
    const tbody = document.getElementById('audit-table-body');
    if (tbody) tbody.innerHTML = this.renderSkeletonRows(7, 6);

    try {
      const logs = await api.getAuditLogs({ limit: 100 });
      if (!tbody) return;

      if (logs.length === 0) {
        const isMgr = api.user?.role === 'MANAGER';
        const centerName = this.availableCenters?.[0] || 'your assigned branch';
        tbody.innerHTML = this.renderEmptyState(
          '🛡️',
          'Audit Log is Empty',
          isMgr ? `No security audit events recorded yet for employees in ${centerName}.` : 'Append-only system security logs will appear as operations are executed.'
        );
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
      if (tbody) tbody.innerHTML = this.renderErrorState('Failed to retrieve system audit records from server.', 'app.loadAuditLogs()');
      this.showToast('Failed to load audit logs', 'error');
    }
  }

  // =========================================================================
  // 7. Attendance Operations & Live Clock-In/Out
  // =========================================================================
  parseUtcDate(dateStr) {
    if (!dateStr) return new Date();
    let s = String(dateStr).trim();
    if (!s.endsWith('Z') && !s.includes('+') && !/[0-9]-[0-9]{2}:[0-9]{2}$/.test(s)) {
      s = s.replace(' ', 'T') + 'Z';
    }
    const d = new Date(s);
    return isNaN(d.getTime()) ? new Date() : d;
  }

  async loadAttendanceData() {
    try {
      const summary = await api.getAttendanceSummary();
      
      // Update Summary KPIs
      const kpiDays = document.getElementById('att-kpi-days');
      const kpiHours = document.getElementById('att-kpi-hours');
      const kpiAvg = document.getElementById('att-kpi-avg');
      const kpiPunct = document.getElementById('att-kpi-punctuality');
      const kpiPunctSub = document.getElementById('att-kpi-punctuality-sub');

      if (kpiDays) kpiDays.innerText = `${summary.total_days_present} Days`;
      if (kpiHours) kpiHours.innerText = `${summary.total_working_hours} hrs`;
      if (kpiAvg) kpiAvg.innerText = `${summary.average_daily_hours} hrs`;

      if (kpiPunct) {
        if (summary.total_days_present === 0) {
          kpiPunct.innerText = `0.0%`;
          if (kpiPunctSub) {
            kpiPunctSub.innerText = 'No shifts logged yet';
            kpiPunctSub.style.color = 'var(--text-muted)';
          }
        } else {
          kpiPunct.innerText = `${summary.on_time_rate_percent}%`;
          if (kpiPunctSub) {
            if (summary.on_time_rate_percent >= 90) {
              kpiPunctSub.innerText = 'Excellent punctuality';
              kpiPunctSub.style.color = '#34d399';
            } else if (summary.on_time_rate_percent >= 75) {
              kpiPunctSub.innerText = 'Good punctuality';
              kpiPunctSub.style.color = '#60a5fa';
            } else {
              kpiPunctSub.innerText = 'Needs improvement';
              kpiPunctSub.style.color = '#f59e0b';
            }
          }
        }
      }

      // Update Employee Widget Card state
      this.updateAttendanceWidgetState(summary);

      // Load History Table
      await this.loadAttendanceHistory();

      // If Manager/Admin, load Live Team Roster
      if (api.user?.role !== 'EMPLOYEE') {
        await this.loadLiveTeamStatus();
      }
    } catch (err) {
      console.warn('Attendance load error:', err);
    }
  }

  updateAttendanceWidgetState(summary) {
    this.currentAttendanceSummary = summary;
    const badges = document.querySelectorAll('.attendance-status-badge, #emp-attendance-status-badge, #admin-attendance-status-badge');
    const punctBadges = document.querySelectorAll('.punctuality-badge, #emp-punctuality-badge, #admin-punctuality-badge');
    const otBadges = document.querySelectorAll('.overtime-badge, #emp-overtime-badge, #admin-overtime-badge');
    const timers = document.querySelectorAll('.attendance-stopwatch, #emp-attendance-timer, #admin-attendance-timer');
    const breakLabels = document.querySelectorAll('.break-duration-label, #emp-break-label, #admin-break-label');
    const detailsEls = document.querySelectorAll('.attendance-details-text, #emp-attendance-details, #admin-attendance-details');
    const deviceTags = document.querySelectorAll('.device-tag, #admin-device-tag');
    const btnsIn = document.querySelectorAll('.btn-clock-in, #btn-emp-clock-in');
    const btnsBreak = document.querySelectorAll('.btn-break-toggle, #btn-emp-break');
    const btnsOut = document.querySelectorAll('.btn-clock-out, #btn-emp-clock-out');
    const progressBars = document.querySelectorAll('.shift-progress-bar, #emp-shift-bar, #admin-shift-bar');
    const progressPercents = document.querySelectorAll('.shift-progress-percent, #emp-shift-percent, #admin-shift-percent');

    if (summary.is_currently_clocked_in && summary.today_record) {
      const rec = summary.today_record;
      const clockInTime = this.parseUtcDate(rec.clock_in);
      const isOnBreak = summary.is_on_break;

      // Badges
      badges.forEach(b => {
        if (isOnBreak) {
          b.innerText = '☕ ON BREAK';
          b.style.background = 'rgba(245, 158, 11, 0.2)';
          b.style.color = '#fbbf24';
        } else {
          b.innerText = 'ONLINE / ON DUTY';
          b.style.background = 'rgba(16, 185, 129, 0.2)';
          b.style.color = '#34d399';
        }
      });

      // Punctuality Badge
      punctBadges.forEach(pb => {
        pb.style.display = 'inline-flex';
        if (rec.punctuality_status === 'EARLY') {
          pb.innerText = '🟢 Early Arrival';
          pb.style.background = 'rgba(16, 185, 129, 0.15)';
          pb.style.color = '#34d399';
        } else if (rec.punctuality_status === 'LATE') {
          pb.innerText = `🟡 Late by ${rec.late_minutes || 0}m`;
          pb.style.background = 'rgba(245, 158, 11, 0.15)';
          pb.style.color = '#fbbf24';
        } else {
          pb.innerText = '🟢 On-Time';
          pb.style.background = 'rgba(16, 185, 129, 0.15)';
          pb.style.color = '#34d399';
        }
      });

      // Device Tag
      deviceTags.forEach(dt => {
        dt.innerText = `📍 IP: ${rec.ip_address || '127.0.0.1'} • ${rec.device_info || 'Web Browser'}`;
      });

      // Buttons
      btnsIn.forEach(b => b.disabled = true);
      btnsOut.forEach(b => b.disabled = false);
      btnsBreak.forEach(b => {
        b.style.display = 'inline-flex';
        if (isOnBreak) {
          b.innerText = '▶ Resume Work';
          b.className = 'btn btn-primary btn-sm btn-break-toggle';
        } else {
          b.innerText = '☕ Take Break';
          b.className = 'btn btn-warning btn-sm btn-break-toggle';
        }
      });

      detailsEls.forEach(d => {
        const inStr = clockInTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        d.innerText = `Clocked in at ${inStr} IST (${rec.scheduled_shift || 'General Shift'})`;
      });

      this.startAttendanceStopwatch(rec);
    } else if (summary.today_record && summary.today_record.clock_out) {
      const rec = summary.today_record;
      if (this.attendanceStopwatchInterval) {
        clearInterval(this.attendanceStopwatchInterval);
        this.attendanceStopwatchInterval = null;
      }

      badges.forEach(b => {
        b.innerText = 'SHIFT COMPLETED';
        b.style.background = 'rgba(59, 130, 246, 0.2)';
        b.style.color = '#60a5fa';
      });
      punctBadges.forEach(pb => pb.style.display = 'none');
      otBadges.forEach(ob => ob.style.display = rec.status === 'OVERTIME' ? 'inline-flex' : 'none');
      btnsIn.forEach(b => b.disabled = false);
      btnsOut.forEach(b => b.disabled = true);
      btnsBreak.forEach(b => b.style.display = 'none');
      breakLabels.forEach(bl => {
        const breakMins = Math.floor((rec.total_break_seconds || 0) / 60);
        if (breakMins > 0) {
          bl.style.display = 'block';
          bl.innerText = `☕ Total Break: ${breakMins} mins`;
        } else {
          bl.style.display = 'none';
        }
      });

      const clockInTime = this.parseUtcDate(rec.clock_in);
      const clockOutTime = this.parseUtcDate(rec.clock_out);
      detailsEls.forEach(d => {
        d.innerText = `Shift ended at ${clockOutTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (${rec.total_hours} hrs active logged)`;
      });

      let totalSec = rec.elapsed_seconds;
      if (totalSec === undefined || totalSec === null) {
        totalSec = Math.max(0, Math.floor((clockOutTime.getTime() - clockInTime.getTime()) / 1000) - (rec.total_break_seconds || 0));
      }
      const hrs = String(Math.floor(totalSec / 3600)).padStart(2, '0');
      const mins = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
      const secs = String(totalSec % 60).padStart(2, '0');
      timers.forEach(t => {
        t.innerText = `${hrs}:${mins}:${secs}`;
        t.style.color = '#60a5fa';
      });

      const pct = Math.min(100, Math.round(((rec.total_hours || 0) / 8.0) * 100));
      progressBars.forEach(pb => pb.style.width = `${pct}%`);
      progressPercents.forEach(pp => pp.innerText = `${pct}% (${rec.total_hours || 0} / 8.0 hrs)`);
    } else {
      if (this.attendanceStopwatchInterval) {
        clearInterval(this.attendanceStopwatchInterval);
        this.attendanceStopwatchInterval = null;
      }
      badges.forEach(b => {
        b.innerText = 'NOT CLOCKED IN';
        b.style.background = 'rgba(100, 116, 139, 0.2)';
        b.style.color = '#94a3b8';
      });
      punctBadges.forEach(pb => pb.style.display = 'none');
      otBadges.forEach(ob => ob.style.display = 'none');
      btnsIn.forEach(b => b.disabled = false);
      btnsOut.forEach(b => b.disabled = true);
      btnsBreak.forEach(b => b.style.display = 'none');
      breakLabels.forEach(bl => bl.style.display = 'none');
      detailsEls.forEach(d => d.innerText = 'Shift not started • General Shift (09:00 AM - 06:00 PM)');
      timers.forEach(t => {
        t.innerText = '00:00:00';
        t.style.color = '#34d399';
      });
      progressBars.forEach(pb => pb.style.width = '0%');
      progressPercents.forEach(pp => pp.innerText = '0% (0.0 / 8.0 hrs)');
    }
  }

  startAttendanceStopwatch(todayRecord) {
    if (this.attendanceStopwatchInterval) {
      clearInterval(this.attendanceStopwatchInterval);
      this.attendanceStopwatchInterval = null;
    }
    if (!todayRecord || !todayRecord.clock_in) return;

    const clockInTime = this.parseUtcDate(todayRecord.clock_in).getTime();
    const breakAccumulatedSec = todayRecord.total_break_seconds || 0;
    const isOnBreak = !!todayRecord.is_on_break;
    const breakStartTime = todayRecord.break_start ? this.parseUtcDate(todayRecord.break_start).getTime() : Date.now();

    const updateTimer = () => {
      const now = Date.now();
      let currentBreakSec = 0;
      if (isOnBreak) {
        currentBreakSec = Math.max(0, Math.floor((now - breakStartTime) / 1000));
      }

      const totalBreakSec = breakAccumulatedSec + currentBreakSec;
      const grossSec = Math.max(0, Math.floor((now - clockInTime) / 1000));
      const netWorkingSec = Math.max(0, grossSec - totalBreakSec);

      const hrs = String(Math.floor(netWorkingSec / 3600)).padStart(2, '0');
      const mins = String(Math.floor((netWorkingSec % 3600) / 60)).padStart(2, '0');
      const secs = String(netWorkingSec % 60).padStart(2, '0');
      const timeStr = `${hrs}:${mins}:${secs}`;

      document.querySelectorAll('.attendance-stopwatch, #emp-attendance-timer, #admin-attendance-timer').forEach(el => {
        el.innerText = timeStr;
        el.style.color = isOnBreak ? '#fbbf24' : (netWorkingSec >= 8 * 3600 ? '#c084fc' : '#34d399');
      });

      // Update Break Duration Labels
      document.querySelectorAll('.break-duration-label, #emp-break-label, #admin-break-label').forEach(el => {
        if (totalBreakSec > 0 || isOnBreak) {
          el.style.display = 'block';
          const bHrs = String(Math.floor(totalBreakSec / 3600)).padStart(2, '0');
          const bMins = String(Math.floor((totalBreakSec % 3600) / 60)).padStart(2, '0');
          const bSecs = String(totalBreakSec % 60).padStart(2, '0');
          el.innerText = `☕ Total Break: ${bHrs}:${bMins}:${bSecs} ${isOnBreak ? '(Active)' : ''}`;
        } else {
          el.style.display = 'none';
        }
      });

      // Overtime badge & progress bar
      const netHours = netWorkingSec / 3600.0;
      const isOvertime = netHours >= 8.0;
      document.querySelectorAll('.overtime-badge, #emp-overtime-badge, #admin-overtime-badge').forEach(ob => {
        if (isOvertime) {
          ob.style.display = 'inline-flex';
          const otSec = netWorkingSec - 8 * 3600;
          const otH = Math.floor(otSec / 3600);
          const otM = Math.floor((otSec % 3600) / 60);
          ob.innerText = `🔥 Overtime (+${otH}h ${otM}m)`;
        } else {
          ob.style.display = 'none';
        }
      });

      const pct = Math.min(100, Math.round((netHours / 8.0) * 100));
      document.querySelectorAll('.shift-progress-bar, #emp-shift-bar, #admin-shift-bar').forEach(pb => {
        pb.style.width = `${pct}%`;
        pb.style.background = isOvertime ? 'linear-gradient(90deg, #10b981, #a855f7)' : 'linear-gradient(90deg, #3b82f6, #10b981)';
      });
      document.querySelectorAll('.shift-progress-percent, #emp-shift-percent, #admin-shift-percent').forEach(pp => {
        pp.innerText = `${pct}% (${netHours.toFixed(1)} / 8.0 hrs)${isOvertime ? ' • 🎯 Target Met!' : ''}`;
      });
    };

    updateTimer();
    this.attendanceStopwatchInterval = setInterval(updateTimer, 1000);
  }

  getBrowserAndDeviceInfo() {
    const ua = navigator.userAgent;
    let browser = "Web Browser";
    let os = "Desktop";

    if (ua.includes("Edg")) browser = "Microsoft Edge";
    else if (ua.includes("Chrome")) browser = "Google Chrome";
    else if (ua.includes("Safari")) browser = "Apple Safari";
    else if (ua.includes("Firefox")) browser = "Mozilla Firefox";

    if (ua.includes("iPhone") || ua.includes("iPad")) os = "iOS Device";
    else if (ua.includes("Android")) os = "Android Mobile";
    else if (ua.includes("Windows")) os = "Windows 10/11";
    else if (ua.includes("Macintosh")) os = "macOS";
    else if (ua.includes("Linux")) os = "Linux";

    return `${browser} on ${os}`;
  }

  async handleClockIn() {
    try {
      const deviceInfo = this.getBrowserAndDeviceInfo();
      const res = await api.clockIn('', deviceInfo);
      
      // Populate and Show Clock-In Confirmation Success Modal
      const now = new Date();
      const timeElem = document.getElementById('clockin-modal-time');
      const punctElem = document.getElementById('clockin-modal-punctuality');
      const shiftElem = document.getElementById('clockin-modal-shift');
      const deviceElem = document.getElementById('clockin-modal-device');

      if (timeElem) timeElem.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' IST';
      if (punctElem) {
        if (res.punctuality_status === 'EARLY') {
          punctElem.innerText = '🟢 Early Arrival';
          punctElem.style.background = 'rgba(16,185,129,0.2)';
          punctElem.style.color = '#34d399';
        } else if (res.punctuality_status === 'LATE') {
          punctElem.innerText = `🟡 Late by ${res.late_minutes || 0} mins`;
          punctElem.style.background = 'rgba(245,158,11,0.2)';
          punctElem.style.color = '#fbbf24';
        } else {
          punctElem.innerText = '🟢 On-Time / Punctual';
          punctElem.style.background = 'rgba(16,185,129,0.2)';
          punctElem.style.color = '#34d399';
        }
      }
      if (shiftElem) shiftElem.innerText = res.scheduled_shift || 'General Shift (09:00 AM – 06:00 PM)';
      if (deviceElem) deviceElem.innerText = `IP: ${res.ip_address || '127.0.0.1'} • ${res.device_info || deviceInfo}`;

      const modal = document.getElementById('modal-clockin-success');
      if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
      }

      this.showToast('Successfully clocked in! Work stopwatch started.', 'success');
      await this.loadAttendanceData();
    } catch (err) {
      this.showToast(err.message || 'Clock in failed', 'error');
    }
  }

  async handleToggleBreak() {
    try {
      const summary = this.currentAttendanceSummary;
      if (!summary || !summary.is_currently_clocked_in) {
        this.showToast('Please clock in before managing breaks.', 'error');
        return;
      }

      if (summary.is_on_break) {
        await api.endBreak();
        this.showToast('Break ended. Resumed active shift!', 'success');
      } else {
        await api.startBreak();
        this.showToast('Break started. Take your time!', 'info');
      }
      await this.loadAttendanceData();
    } catch (err) {
      this.showToast(err.message || 'Break toggle failed', 'error');
    }
  }

  async handleClockOut() {
    const summary = this.currentAttendanceSummary;
    let detailsSummary = 'Are you ready to clock out and finalize your working hours for today?';
    if (summary && summary.today_record) {
      const rec = summary.today_record;
      const clockInTime = this.parseUtcDate(rec.clock_in).getTime();
      const grossSec = Math.max(0, Math.floor((Date.now() - clockInTime) / 1000));
      const netSec = Math.max(0, grossSec - (rec.total_break_seconds || 0));
      const netH = (netSec / 3600.0).toFixed(1);
      const breakM = Math.floor((rec.total_break_seconds || 0) / 60);
      const isOt = netSec >= 8 * 3600;
      detailsSummary = `You have logged ${netH} hrs of active work today (Break: ${breakM}m). ${isOt ? '🔥 Overtime verified.' : ''} Click Proceed to seal today's shift.`;
    }

    const confirmed = await this.confirmAction({
      title: 'Clock Out & End Shift',
      message: detailsSummary,
      proceedText: 'Clock Out',
      badge: 'ATTENDANCE SHIFT CLOSURE'
    });
    if (!confirmed) return;

    if (this.attendanceStopwatchInterval) {
      clearInterval(this.attendanceStopwatchInterval);
      this.attendanceStopwatchInterval = null;
    }

    try {
      const res = await api.clockOut();
      const otMsg = res.overtime_hours > 0 ? ` (Includes ${res.overtime_hours} hrs Overtime 🔥)` : '';
      this.showToast(`Clocked out successfully! Logged ${res.total_hours} hrs today${otMsg}.`, 'success');
      await this.loadAttendanceData();
    } catch (err) {
      this.showToast(err.message || 'Clock out failed', 'error');
    }
  }

  async loadAttendanceHistory() {
    const tbody = document.getElementById('attendance-table-body');
    if (tbody) tbody.innerHTML = this.renderSkeletonRows(8, 5);

    try {
      const centerFilter = document.getElementById('att-center-filter')?.value || 'ALL';
      const history = await api.getAttendanceHistory({ center: centerFilter, page_size: 50 });
      if (!tbody) return;

      if (history.length === 0) {
        tbody.innerHTML = this.renderEmptyState(
          '⏱️',
          'No Attendance Records Found',
          'No check-in or shift sessions logged for the selected center filter.'
        );
        return;
      }

      tbody.innerHTML = history.map(rec => {
        const inTime = rec.clock_in ? this.parseUtcDate(rec.clock_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
        const outTime = rec.clock_out ? this.parseUtcDate(rec.clock_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '<span style="color:#34d399; font-weight:600;">ACTIVE</span>';
        const breakM = Math.floor((rec.total_break_seconds || 0) / 60);
        
        let statusBadge = `<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399;">PRESENT</span>`;
        if (rec.status === 'OVERTIME') statusBadge = `<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc;">🔥 OVERTIME</span>`;
        else if (rec.status === 'HALF_DAY') statusBadge = `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24;">HALF DAY</span>`;
        else if (rec.status === 'LATE' || rec.punctuality_status === 'LATE') statusBadge = `<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171;">LATE (${rec.late_minutes}m)</span>`;

        return `
          <tr>
            <td><strong>${rec.work_date}</strong></td>
            <td><b>${rec.employee_name || '#' + rec.employee_id}</b> <small style="color:var(--text-muted);">(#${rec.employee_id})</small></td>
            <td>${rec.center || 'Corporate HQ'}</td>
            <td><code>${inTime}</code></td>
            <td><code>${outTime}</code></td>
            <td>
              <strong style="color:${rec.total_hours >= 8 ? '#34d399' : '#94a3b8'}">${rec.total_hours} hrs</strong>
              ${breakM > 0 ? `<small style="color:var(--text-muted); display:block; font-size:0.7rem;">(${breakM}m break)</small>` : ''}
            </td>
            <td>${statusBadge}</td>
            <td><small style="color:var(--text-muted); font-size:0.72rem;">${rec.device_info || 'Web'}</small></td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      if (tbody) tbody.innerHTML = this.renderErrorState('Failed to retrieve attendance logs from server.', 'app.loadAttendanceHistory()');
      console.warn('Attendance history error:', err);
    }
  }

  async loadLiveTeamStatus() {
    try {
      const data = await api.getLiveTeamStatus();
      const board = document.getElementById('att-live-team-board');
      const list = document.getElementById('att-live-team-list');
      if (!board || !list) return;

      board.style.display = 'block';

      if (!data.active_employees || data.active_employees.length === 0) {
        list.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:10px;">No employees are currently checked in today.</div>`;
        return;
      }

      list.innerHTML = data.active_employees.map(emp => `
        <div class="live-on-duty-badge">
          <span style="width:8px; height:8px; border-radius:50%; background:#10b981; display:inline-block; box-shadow:0 0 8px #10b981;"></span>
          <div>
            <strong style="color:#fff;">${emp.employee_name || '#' + emp.employee_id}</strong>
            <div style="font-size:0.72rem; color:var(--text-muted);">${emp.center || 'HQ'} • In since ${new Date(emp.clock_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.warn('Live team status error:', err);
    }
  }

  // =========================================================================
  // 8. Performance Reviews & Appraisals
  // =========================================================================
  async loadPerformanceReviews() {
    const container = document.getElementById('performance-reviews-container');
    if (container) {
      container.innerHTML = `
        <div class="review-card skeleton-shimmer" style="height: 180px; margin-bottom: 16px;"></div>
        <div class="review-card skeleton-shimmer" style="height: 180px;"></div>
      `;
    }

    try {
      const reviews = await api.getPerformanceReviews();
      if (!container) return;

      if (reviews.length === 0) {
        container.innerHTML = `
          <div class="empty-state-box">
            <div class="empty-state-icon">⭐</div>
            <div class="empty-state-title">No Performance Appraisals Published Yet</div>
            <div class="empty-state-desc">Quarterly performance appraisals authored by managers will appear here.</div>
            ${api.user?.role !== 'EMPLOYEE' ? '<button class="btn btn-primary btn-sm" onclick="app.openAddReviewModal()" style="margin-top: 10px;">+ Author Review</button>' : ''}
          </div>
        `;
        return;
      }

      container.innerHTML = reviews.map(rev => {
        const stars = '★'.repeat(Math.round(rev.rating)) + '☆'.repeat(Math.max(0, 5 - Math.round(rev.rating)));
        let goalBadge = `<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399;">${rev.goals_met}</span>`;
        if (rev.goals_met === 'EXCEEDED') goalBadge = `<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc;">🌟 EXCEEDED</span>`;
        else if (rev.goals_met === 'NEEDS_IMPROVEMENT') goalBadge = `<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171;">NEEDS IMPROVEMENT</span>`;

        const isOwnReview = rev.employee_id === api.user?.employee_id;
        const ackSection = rev.is_acknowledged
          ? `<div style="margin-top:14px; padding:10px 14px; background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2); border-radius:6px; font-size:0.8rem; color:#34d399;">
               ✓ <b>Acknowledged by Employee</b> on ${new Date(rev.acknowledged_at).toLocaleDateString()}
               ${rev.employee_comments ? `<div style="color:var(--text-secondary); margin-top:4px;"><i>"${rev.employee_comments}"</i></div>` : ''}
             </div>`
          : (isOwnReview
              ? `<div style="margin-top:14px;">
                   <button class="btn btn-primary btn-sm" onclick="app.openAckReviewModal(${rev.id})">Acknowledge Appraisal</button>
                 </div>`
              : `<div style="margin-top:14px; font-size:0.8rem; color:var(--text-muted);">⏳ Pending employee acknowledgement</div>`);

        return `
          <div class="review-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
              <div>
                <div style="font-size:1.1rem; font-weight:700; color:#fff;">
                  ${rev.employee_name || 'Employee #' + rev.employee_id} 
                  <small style="font-size:0.8rem; color:var(--text-muted); font-weight:normal;">(${rev.position || 'Staff'} • ${rev.center || 'HQ'})</small>
                </div>
                <div style="font-size:0.82rem; color:var(--primary); font-weight:600; margin-top:2px;">Cycle: ${rev.review_period}</div>
              </div>
              <div style="text-align:right;">
                <div class="star-rating-display">${stars} <span style="font-size:1rem; font-weight:700; color:#fff;">${rev.rating.toFixed(1)}/5.0</span></div>
                <div style="margin-top:4px;">${goalBadge}</div>
              </div>
            </div>

            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin: 12px 0;">
              ${rev.strengths ? `
                <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:6px; border-left:3px solid #34d399;">
                  <div style="font-size:0.75rem; color:#34d399; font-weight:700; text-transform:uppercase;">Key Strengths</div>
                  <div style="font-size:0.84rem; color:var(--text-secondary); margin-top:4px; line-height:1.4;">${rev.strengths}</div>
                </div>` : ''}
              ${rev.areas_for_improvement ? `
                <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:6px; border-left:3px solid #f59e0b;">
                  <div style="font-size:0.75rem; color:#fbbf24; font-weight:700; text-transform:uppercase;">Areas for Development</div>
                  <div style="font-size:0.84rem; color:var(--text-secondary); margin-top:4px; line-height:1.4;">${rev.areas_for_improvement}</div>
                </div>` : ''}
            </div>

            <div style="background:rgba(15,23,42,0.6); padding:14px; border-radius:6px; border:1px solid rgba(255,255,255,0.05); margin-top:10px;">
              <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Manager Feedback</div>
              <div style="font-size:0.88rem; color:#f1f5f9; margin-top:4px; line-height:1.5;">${rev.manager_feedback}</div>
            </div>

            ${ackSection}
          </div>
        `;
      }).join('');
    } catch (err) {
      if (container) {
        container.innerHTML = `
          <div class="empty-state-box" style="border: 1px solid rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.04);">
            <div class="empty-state-icon">⚠️</div>
            <div class="empty-state-title" style="color: #f87171;">Connection Error</div>
            <div class="empty-state-desc">Failed to load performance appraisals from server.</div>
            <button class="btn btn-secondary btn-sm" onclick="app.loadPerformanceReviews()" style="margin-top: 10px;">🔄 Retry Request</button>
          </div>
        `;
      }
      console.warn('Performance reviews error:', err);
    }
  }

  openAddReviewModal() {
    this.closeModals();
    const form = document.getElementById('form-add-performance');
    if (form) form.reset();
    const modal = document.getElementById('modal-add-performance');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
  }

  async handleAddPerformanceReview(e) {
    e.preventDefault();
    const data = {
      employee_id: parseInt(document.getElementById('review-emp-id').value),
      review_period: document.getElementById('review-period').value.trim(),
      rating: parseFloat(document.getElementById('review-rating').value),
      goals_met: document.getElementById('review-goals').value,
      strengths: document.getElementById('review-strengths').value.trim() || null,
      areas_for_improvement: document.getElementById('review-areas').value.trim() || null,
      manager_feedback: document.getElementById('review-feedback').value.trim(),
      status: 'FINALIZED'
    };

    try {
      await api.createPerformanceReview(data);
      this.showToast('Performance appraisal published successfully!', 'success');
      this.closeModals();
      await this.loadPerformanceReviews();
    } catch (err) {
      this.showToast(err.message || 'Failed to publish review', 'error');
    }
  }

  openAckReviewModal(reviewId) {
    this.closeModals();
    document.getElementById('ack-review-id').value = reviewId;
    const modal = document.getElementById('modal-ack-performance');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
  }

  async handleAckPerformanceReview(e) {
    e.preventDefault();
    const reviewId = document.getElementById('ack-review-id').value;
    const comments = document.getElementById('ack-employee-comments').value.trim();

    try {
      await api.acknowledgePerformanceReview(reviewId, comments);
      this.showToast('Appraisal acknowledged successfully!', 'success');
      this.closeModals();
      await this.loadPerformanceReviews();
    } catch (err) {
      this.showToast(err.message || 'Acknowledgement failed', 'error');
    }
  }

  // =========================================================================
  // 9. Document Vault & File Management
  // =========================================================================
  async loadDocuments() {
    const grid = document.getElementById('documents-grid');
    if (grid) {
      grid.innerHTML = `
        <div class="doc-card skeleton-shimmer" style="height: 160px;"></div>
        <div class="doc-card skeleton-shimmer" style="height: 160px;"></div>
        <div class="doc-card skeleton-shimmer" style="height: 160px;"></div>
      `;
    }

    try {
      const isManagerOrAdmin = api.user?.role !== 'EMPLOYEE';
      const selectorWrap = document.getElementById('doc-emp-selector-wrap');
      const filterSelect = document.getElementById('doc-filter-employee');

      if (isManagerOrAdmin && selectorWrap && filterSelect) {
        selectorWrap.style.display = 'block';
        if (filterSelect.options.length <= 1) {
          const emps = await api.getEmployees({ status: 'ACTIVE' });
          const myEid = api.user?.employee_id;
          filterSelect.innerHTML = `<option value="${myEid}">My Personal Documents (#${myEid})</option>` +
            emps
              .filter(e => e.eid !== myEid)
              .map(e => `<option value="${e.eid}">${e.ename} (#${e.eid} • ${e.ecen})</option>`)
              .join('');
        }
      } else if (selectorWrap) {
        selectorWrap.style.display = 'none';
      }

      const selectedEid = (isManagerOrAdmin && filterSelect?.value) ? parseInt(filterSelect.value) : api.user?.employee_id;
      if (!selectedEid) return;

      const docs = await api.getEmployeeDocuments(selectedEid);
      if (!grid) return;

      if (docs.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1;">
            <div class="empty-state-box">
              <div class="empty-state-icon">📁</div>
              <div class="empty-state-title">Document Vault is Empty</div>
              <div class="empty-state-desc">Upload ID proofs, degree certificates, and signed agreements for permanent compliance archiving.</div>
              <button class="btn btn-primary btn-sm" onclick="app.openUploadDocModal()" style="margin-top: 10px;">+ Upload First File</button>
            </div>
          </div>
        `;
        return;
      }

      const iconMap = {
        ID_PROOF: '🪪',
        CONTRACT: '📝',
        CERTIFICATE: '🎓',
        TAX_FORM: '📑',
        RESUME: '📄',
        OTHER: '📁'
      };

      grid.innerHTML = docs.map(doc => {
        const icon = iconMap[doc.document_type] || '📁';
        const sizeKb = (doc.file_size / 1024).toFixed(1);
        const downloadUrl = api.getDocumentDownloadUrl(doc.id);

        return `
          <div class="doc-card">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                <div class="doc-icon-wrap">${icon}</div>
                <span class="badge badge-primary">${doc.document_type}</span>
              </div>
              <div style="font-weight:700; font-size:0.95rem; color:#fff; line-height:1.3;">${doc.title}</div>
              <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">${doc.file_name} (${sizeKb} KB)</div>
              <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">Uploaded: ${new Date(doc.created_at).toLocaleDateString()}</div>
            </div>

            <div style="display:flex; gap:8px; margin-top:10px; border-top:1px solid var(--border-color); padding-top:10px;">
              <a href="${downloadUrl}" target="_blank" class="btn btn-secondary btn-sm" style="flex:1; text-align:center; text-decoration:none; justify-content:center;">
                ⬇ Download
              </a>
              <button class="btn btn-secondary btn-sm" onclick="app.handleDeleteDocument(${doc.id}, '${doc.title.replace(/'/g, "\\'")}')" style="color:#f87171;">
                ✕
              </button>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      if (grid) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1;">
            <div class="empty-state-box" style="border: 1px solid rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.04);">
              <div class="empty-state-icon">⚠️</div>
              <div class="empty-state-title" style="color: #f87171;">Connection Error</div>
              <div class="empty-state-desc">Failed to load archived documents from server.</div>
              <button class="btn btn-secondary btn-sm" onclick="app.loadDocuments()" style="margin-top: 10px;">🔄 Retry Request</button>
            </div>
          </div>
        `;
      }
      console.warn('Load documents error:', err);
    }
  }

  openUploadDocModal() {
    this.closeModals();
    const form = document.getElementById('form-upload-document');
    if (form) form.reset();
    const modal = document.getElementById('modal-upload-document');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
  }

  async handleUploadDocument(e) {
    e.preventDefault();
    const title = document.getElementById('doc-title').value.trim();
    const type = document.getElementById('doc-type').value;
    const fileInput = document.getElementById('doc-file-input');
    const targetEid = document.getElementById('doc-target-eid')?.value;

    if (!fileInput.files || fileInput.files.length === 0) {
      this.showToast('Please choose a file to upload', 'warning');
      return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('document_type', type);
    formData.append('file', fileInput.files[0]);
    if (targetEid) formData.append('target_employee_id', targetEid);

    const btnSubmit = document.getElementById('btn-submit-doc-upload');
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerText = 'Uploading...';
    }

    try {
      await api.uploadDocument(formData);
      this.showToast('Document uploaded and archived securely!', 'success');
      this.closeModals();
      await this.loadDocuments();
    } catch (err) {
      this.showToast(err.message || 'Upload failed', 'error');
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerText = 'Upload File';
      }
    }
  }

  async handleDeleteDocument(docId, title) {
    const confirmed = await this.confirmAction({
      title: 'Delete Compliance Document',
      message: `Are you sure you want to permanently delete <b>"${title}"</b> from the document vault?`,
      proceedText: 'Delete Document',
      isDanger: true,
      badge: 'PERMANENT DELETION'
    });
    if (!confirmed) return;

    try {
      await api.deleteDocument(docId);
      this.showToast('Document deleted.', 'info');
      await this.loadDocuments();
    } catch (err) {
      this.showToast(err.message || 'Delete failed', 'error');
    }
  }

  // =========================================================================
  // 10. Notification Center & Alerts
  // =========================================================================
  async loadNotifications() {
    if (!api.token) return;
    try {
      const feed = await api.getNotifications();
      const badge = document.getElementById('notification-badge');
      const list = document.getElementById('notification-feed-list');

      if (badge) {
        if (feed.unread_count > 0) {
          badge.innerText = feed.unread_count > 9 ? '9+' : feed.unread_count;
          badge.style.display = 'inline-block';
        } else {
          badge.style.display = 'none';
        }
      }

      if (list) {
        if (!feed.notifications || feed.notifications.length === 0) {
          list.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted); font-size:0.8rem;">No notifications right now.</div>`;
          return;
        }

        list.innerHTML = feed.notifications.map(n => `
          <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="app.handleNotificationClick(${n.id}, '${n.action_url || ''}')">
            <div class="notification-item-title">${n.title}</div>
            <div class="notification-item-msg">${n.message}</div>
            <div class="notification-item-time">${new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • ${new Date(n.created_at).toLocaleDateString()}</div>
          </div>
        `).join('');
      }
    } catch (err) {
      console.warn('Notifications poll error:', err);
    }
  }

  toggleNotificationDropdown() {
    const drop = document.getElementById('notification-dropdown');
    if (!drop) return;
    drop.style.display = drop.style.display === 'none' ? 'flex' : 'none';
  }

  async handleNotificationClick(notifId, actionUrl) {
    try {
      await api.markNotificationRead(notifId);
      await this.loadNotifications();
      if (actionUrl) {
        const view = actionUrl.replace('#', '');
        if (view) this.switchView(view);
      }
      const drop = document.getElementById('notification-dropdown');
      if (drop) drop.style.display = 'none';
    } catch (err) {
      console.warn(err);
    }
  }

  async markAllNotificationsRead() {
    try {
      await api.markAllNotificationsRead();
      this.showToast('All notifications marked as read.', 'info');
      await this.loadNotifications();
    } catch (err) {
      this.showToast('Failed to mark notifications', 'error');
    }
  }

  startNotificationPolling() {
    if (this.notificationInterval) clearInterval(this.notificationInterval);
    this.notificationInterval = setInterval(() => {
      if (api.token) this.loadNotifications();
    }, 25000);
  }

  // =========================================================================
  // Spotlight Command Palette (Ctrl+K)
  // =========================================================================
  toggleCommandPalette() {
    const modal = document.getElementById('modal-command-palette');
    if (!modal) return;
    if (modal.classList.contains('active')) {
      this.closeCommandPalette();
    } else {
      this.openCommandPalette();
    }
  }

  openCommandPalette() {
    const modal = document.getElementById('modal-command-palette');
    const input = document.getElementById('command-palette-input');
    if (!modal || !input) return;
    modal.classList.add('active');
    modal.style.display = 'flex';
    input.value = '';
    input.focus();
    this.filterCommandPalette('');
  }

  closeCommandPalette() {
    const modal = document.getElementById('modal-command-palette');
    if (!modal) return;
    modal.classList.remove('active');
    modal.style.display = 'none';
  }

  handleCommandPaletteBackdrop(e) {
    if (e.target.id === 'modal-command-palette') {
      this.closeCommandPalette();
    }
  }

  filterCommandPalette(query) {
    const resultsContainer = document.getElementById('command-palette-results');
    if (!resultsContainer) return;
    const q = query.trim().toLowerCase();
    const role = api.user?.role || 'EMPLOYEE';

    // Base navigation commands
    const navCommands = [
      { icon: '📊', title: role === 'EMPLOYEE' ? 'My Workspace' : 'Executive Dashboard', subtitle: 'View workforce overview and KPIs', action: 'navigate', param: 'dashboard', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '⏱️', title: 'Daily Attendance & Shifts', subtitle: 'Clock in, check break timers, and view roster', action: 'navigate', param: 'attendance', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '👥', title: 'Employee Directory', subtitle: 'Browse roster and management profiles', action: 'navigate', param: 'employees', roles: ['ADMIN', 'MANAGER'] },
      { icon: '💰', title: role === 'EMPLOYEE' ? 'My Payslips' : 'Payroll Operations Hub', subtitle: 'Run batch payroll calculations & download PDF payslips', action: 'navigate', param: 'payroll', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '📅', title: 'Leaves & PTO Portal', subtitle: 'Submit time-off requests and approvals', action: 'navigate', param: 'leaves', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '⭐', title: '360 Performance Appraisals', subtitle: 'Author reviews and employee acknowledgements', action: 'navigate', param: 'performance', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '📁', title: 'Document Vault & Compliance', subtitle: 'Upload and manage contracts & certificates', action: 'navigate', param: 'documents', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '📈', title: 'Workforce Analytics', subtitle: 'Headcount distribution and salary charts', action: 'navigate', param: 'analytics', roles: ['ADMIN', 'MANAGER'] },
      { icon: '🛡️', title: 'Security Audit Vault', subtitle: 'Inspect immutable system event logs', action: 'navigate', param: 'audit', roles: ['ADMIN', 'MANAGER'] },
    ];

    // Quick Actions
    const quickActions = [
      { icon: '▶️', title: 'Clock In for Today', subtitle: 'Record shift start timestamp and location', action: 'clockin', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '☕', title: 'Take / Resume Break', subtitle: 'Toggle active rest break timer', action: 'break', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '⏹️', title: 'Clock Out & Finalize Shift', subtitle: 'Review active hours and close daily record', action: 'clockout', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '📝', title: 'Apply for Leave / PTO', subtitle: 'Submit a new time-off request', action: 'modal_leave', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '🧮', title: 'Open Salary & CTC Calculator', subtitle: 'Simulate gross, tax, and take-home pay', action: 'modal_calc', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '🔒', title: 'Change Security Password', subtitle: 'Update account credentials', action: 'modal_pwd', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] },
      { icon: '🚪', title: 'Sign Out of Apex HRMS', subtitle: 'End current secure session', action: 'logout', roles: ['ADMIN', 'MANAGER', 'EMPLOYEE'] }
    ];

    const filteredNav = navCommands.filter(c => c.roles.includes(role) && (c.title.toLowerCase().includes(q) || c.subtitle.toLowerCase().includes(q)));
    const filteredActions = quickActions.filter(c => c.roles.includes(role) && (c.title.toLowerCase().includes(q) || c.subtitle.toLowerCase().includes(q)));

    let html = '';

    if (filteredNav.length > 0) {
      html += `<div class="command-section-title">Navigation & Modules</div>`;
      html += filteredNav.map((c, i) => `
        <div class="command-item ${i === 0 && !q ? 'focused' : ''}" onclick="app.executeCommand('${c.action}', '${c.param || ''}')">
          <div class="command-item-icon">${c.icon}</div>
          <div class="command-item-content">
            <div class="command-item-title">${c.title}</div>
            <div class="command-item-subtitle">${c.subtitle}</div>
          </div>
          <div class="command-item-key">Jump</div>
        </div>
      `).join('');
    }

    if (filteredActions.length > 0) {
      html += `<div class="command-section-title" style="margin-top: 10px;">Quick Shortcuts</div>`;
      html += filteredActions.map(c => `
        <div class="command-item" onclick="app.executeCommand('${c.action}', '${c.param || ''}')">
          <div class="command-item-icon">${c.icon}</div>
          <div class="command-item-content">
            <div class="command-item-title">${c.title}</div>
            <div class="command-item-subtitle">${c.subtitle}</div>
          </div>
          <div class="command-item-key">Action</div>
        </div>
      `).join('');
    }

    if (!html) {
      html = `
        <div class="empty-state-box" style="padding: 24px 10px;">
          <div class="empty-state-icon" style="font-size: 2rem;">🔍</div>
          <div class="empty-state-title">No matching commands</div>
          <div class="empty-state-desc">Try searching for "attendance", "leave", "payroll", or "password".</div>
        </div>
      `;
    }

    resultsContainer.innerHTML = html;
  }

  handleCommandPaletteKeydown(e) {
    const items = document.querySelectorAll('.command-item');
    let currentIndex = -1;
    items.forEach((el, i) => {
      if (el.classList.contains('focused')) currentIndex = i;
    });

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (items.length === 0) return;
      if (currentIndex >= 0) items[currentIndex].classList.remove('focused');
      const nextIndex = (currentIndex + 1) % items.length;
      items[nextIndex].classList.add('focused');
      items[nextIndex].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (items.length === 0) return;
      if (currentIndex >= 0) items[currentIndex].classList.remove('focused');
      const prevIndex = (currentIndex - 1 + items.length) % items.length;
      items[prevIndex].classList.add('focused');
      items[prevIndex].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const focused = document.querySelector('.command-item.focused') || items[0];
      if (focused) focused.click();
    }
  }

  executeCommand(action, param) {
    this.closeCommandPalette();
    if (action === 'navigate') {
      this.switchView(param);
    } else if (action === 'clockin') {
      this.handleClockIn();
    } else if (action === 'break') {
      this.handleToggleBreak();
    } else if (action === 'clockout') {
      this.handleClockOut();
    } else if (action === 'modal_leave') {
      this.openApplyLeaveModal();
    } else if (action === 'modal_calc') {
      this.openSalaryCalculatorModal();
    } else if (action === 'modal_pwd') {
      this.openChangePasswordModal();
    } else if (action === 'logout') {
      document.getElementById('btn-logout').click();
    }
  }

  // =========================================================================
  // UI Polish: Skeleton Loaders & Rich Empty States
  // =========================================================================
  renderSkeletonRows(colCount, rowCount = 5) {
    return Array.from({ length: rowCount }).map(() => `
      <tr>
        ${Array.from({ length: colCount }).map(() => `
          <td><div class="skeleton-shimmer skeleton-text"></div></td>
        `).join('')}
      </tr>
    `).join('');
  }

  renderEmptyState(icon, title, desc, actionBtnHtml = '') {
    return `
      <tr>
        <td colspan="100" style="padding: 0; border: none;">
          <div class="empty-state-box">
            <div class="empty-state-icon">${icon}</div>
            <div class="empty-state-title">${title}</div>
            <div class="empty-state-desc">${desc}</div>
            ${actionBtnHtml}
          </div>
        </td>
      </tr>
    `;
  }

  renderErrorState(message = 'Failed to load records from server.', retryFnCall = 'app.refreshCurrentView()') {
    return `
      <tr>
        <td colspan="100" style="padding: 0; border: none;">
          <div class="empty-state-box" style="border: 1px solid rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.04);">
            <div class="empty-state-icon" style="font-size: 2.2rem;">⚠️</div>
            <div class="empty-state-title" style="color: #f87171;">Connection Error</div>
            <div class="empty-state-desc">${message}</div>
            <button class="btn btn-secondary btn-sm" onclick="${retryFnCall}" style="margin-top: 12px;">
              <span>🔄</span> Retry Request
            </button>
          </div>
        </td>
      </tr>
    `;
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
    toast.innerHTML = `
      <span>${message}</span>
      <div class="toast-progress"></div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
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
