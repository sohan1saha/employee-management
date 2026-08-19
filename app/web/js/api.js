/**
 * ==============================================================================
 * Apex HRMS - Enterprise API Client Layer
 * ==============================================================================
 * Handles Bearer token headers, HttpOnly cookie credentials, and automatic
 * silent JWT access token refresh on 401 Unauthorized responses.
 */

const API_BASE = '/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token') || null;
    this.refreshToken = localStorage.getItem('refresh_token') || null;
    this.user = JSON.parse(localStorage.getItem('user_info') || 'null');
    this.sessionExpiresAt = parseInt(localStorage.getItem('apex_session_expires_at') || '0', 10);
    this.isRefreshing = false;
    this.refreshSubscribers = [];
    this.baseUrl = API_BASE;
  }

  isSessionValid() {
    if (!this.token || !this.user) return false;
    if (this.sessionExpiresAt && Date.now() >= this.sessionExpiresAt) return false;
    return true;
  }

  getSessionRemainingMs() {
    if (!this.sessionExpiresAt) return 0;
    return Math.max(0, this.sessionExpiresAt - Date.now());
  }

  setSession(accessToken, refreshToken, user, expiresInMinutes = 60) {
    this.token = accessToken;
    if (refreshToken) {
      this.refreshToken = refreshToken;
      localStorage.setItem('refresh_token', refreshToken);
    }
    this.user = user;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user_info', JSON.stringify(user));
    
    // Set 1-hour strict session expiry timestamp
    const expiresAt = Date.now() + (expiresInMinutes * 60 * 1000);
    this.sessionExpiresAt = expiresAt;
    localStorage.setItem('apex_session_expires_at', expiresAt.toString());
    localStorage.setItem('apex_session_started_at', Date.now().toString());
  }

  clearSession() {
    this.token = null;
    this.refreshToken = null;
    this.user = null;
    this.sessionExpiresAt = 0;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('apex_session_expires_at');
    localStorage.removeItem('apex_session_started_at');
  }

  onRefreshed(token) {
    this.refreshSubscribers.map(cb => cb(token));
    this.refreshSubscribers = [];
  }

  subscribeTokenRefresh(cb) {
    this.refreshSubscribers.push(cb);
  }

  async refreshAccessToken() {
    // If the 1-hour session window has expired, refuse refresh and force credential login
    if (this.sessionExpiresAt && Date.now() >= this.sessionExpiresAt) {
      this.clearSession();
      window.dispatchEvent(new CustomEvent('auth:session_expired', {
        detail: { reason: 'Your 1-hour login window has ended. Please sign in again.' }
      }));
      throw new Error('Session expired (1-hour limit reached). Please sign in again.');
    }

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });

      if (!response.ok) {
        throw new Error('Refresh failed');
      }

      const data = await response.json();
      this.setSession(data.access_token, data.refresh_token, data.user, data.expires_in_minutes || 60);
      return data.access_token;
    } catch (err) {
      this.clearSession();
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw err;
    }
  }

  async request(endpoint, options = {}, isRetry = false) {
    // Check 1-hour session expiration before sending request
    if (this.token && this.sessionExpiresAt && Date.now() >= this.sessionExpiresAt) {
      this.clearSession();
      window.dispatchEvent(new CustomEvent('auth:session_expired', {
        detail: { reason: 'Your 1-hour login window has ended. Please sign in again.' }
      }));
      throw new Error('Session expired (1-hour limit reached). Please sign in again.');
    }

    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include' // Sends HttpOnly / SameSite secure cookies
      });

      // Handle 401 Unauthorized
      if (response.status === 401) {
        if (endpoint.startsWith('/auth/login')) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Incorrect Employee ID or password');
        }

        if (endpoint.startsWith('/auth/refresh') || isRetry || (this.sessionExpiresAt && Date.now() >= this.sessionExpiresAt)) {
          this.clearSession();
          window.dispatchEvent(new CustomEvent('auth:session_expired', {
            detail: { reason: 'Session expired. Please sign in again.' }
          }));
          throw new Error('Session expired. Please sign in again.');
        }

        // Silent token refresh flow if within the 1-hour window
        if (!this.isRefreshing) {
          this.isRefreshing = true;
          try {
            const newToken = await this.refreshAccessToken();
            this.isRefreshing = false;
            this.onRefreshed(newToken);
            return await this.request(endpoint, options, true);
          } catch (refreshErr) {
            this.isRefreshing = false;
            throw refreshErr;
          }
        } else {
          // Wait for concurrent refresh to finish
          return new Promise((resolve, reject) => {
            this.subscribeTokenRefresh(async (newToken) => {
              try {
                resolve(await this.request(endpoint, options, true));
              } catch (err) {
                reject(err);
              }
            });
          });
        }
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Request failed with status ${response.status}`);
      }

      // Handle PDF Stream/Blob
      if (response.headers.get('content-type')?.includes('application/pdf')) {
        return await response.blob();
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // --- Auth Endpoints ---
  async login(employee_id, password, remember_me = false) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        employee_id: parseInt(employee_id),
        password,
        remember_me: !!remember_me
      })
    });
    const expireMins = res.expires_in_minutes || 60;
    this.setSession(res.access_token, res.refresh_token, res.user, expireMins);
    return res;
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.clearSession();
    }
  }

  async getMe() {
    return await this.request('/auth/me');
  }

  async changePassword(old_password, new_password, confirm_password) {
    return await this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password, confirm_password })
    });
  }

  // --- Employee Endpoints ---
  async getEmployees(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/employees${query ? '?' + query : ''}`);
  }

  async getNextEmployeeId(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/employees/next-id${query ? '?' + query : ''}`);
  }

  async getEmployee(eid) {
    return await this.request(`/employees/${eid}`);
  }

  async createEmployee(data) {
    return await this.request('/employees', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateEmployee(eid, data) {
    return await this.request(`/employees/${eid}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async deleteEmployee(eid) {
    return await this.request(`/employees/${eid}`, {
      method: 'DELETE'
    });
  }

  async getCenters() {
    return await this.request('/employees/centers/list');
  }

  // --- Analytics Endpoints ---
  async getAnalytics() {
    return await this.request('/analytics/summary');
  }

  // --- Payroll Endpoints ---
  async getPayroll(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/payroll${query ? '?' + query : ''}`);
  }

  async generatePayroll(data) {
    return await this.request('/payroll/generate', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async approvePayroll(recordId) {
    return await this.request(`/payroll/${recordId}/approve`, {
      method: 'POST'
    });
  }

  async downloadPayslip(recordId, filename = 'payslip.pdf') {
    const blob = await this.request(`/payroll/payslip/${recordId}/pdf`);
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  }

  // --- Leave Endpoints ---
  async getLeaves(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/leaves${query ? '?' + query : ''}`);
  }

  async submitLeave(data) {
    return await this.request('/leaves', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateLeaveStatus(leaveId, data) {
    return await this.request(`/leaves/${leaveId}/status`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  // --- Audit Endpoints ---
  async getAuditLogs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/audit/logs${query ? '?' + query : ''}`);
  }

  // --- Attendance Endpoints ---
  async clockIn(notes = '', deviceInfo = '') {
    return await this.request('/attendance/clock-in', {
      method: 'POST',
      body: JSON.stringify({ notes, device_info: deviceInfo })
    });
  }

  async startBreak(notes = '') {
    return await this.request('/attendance/break-start', {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }

  async endBreak() {
    return await this.request('/attendance/break-end', {
      method: 'POST',
      body: JSON.stringify({})
    });
  }

  async clockOut(notes = '') {
    return await this.request('/attendance/clock-out', {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }

  async getAttendanceSummary(employeeId = null) {
    const query = employeeId ? `?employee_id=${employeeId}` : '';
    return await this.request(`/attendance/summary${query}`);
  }

  async getAttendanceHistory(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/attendance/history${query ? '?' + query : ''}`);
  }

  async getLiveTeamStatus() {
    return await this.request('/attendance/live-status');
  }

  // --- Performance Endpoints ---
  async getPerformanceReviews(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/performance/reviews${query ? '?' + query : ''}`);
  }

  async createPerformanceReview(data) {
    return await this.request('/performance/reviews', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async acknowledgePerformanceReview(reviewId, employeeComments = '') {
    return await this.request(`/performance/reviews/${reviewId}/acknowledge`, {
      method: 'PATCH',
      body: JSON.stringify({ employee_comments: employeeComments })
    });
  }

  // --- Document Vault Endpoints ---
  async uploadDocument(formData) {
    // Custom multipart request (bypasses JSON stringify)
    const token = this.token || localStorage.getItem('access_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Document upload failed');
    }
    return await res.json();
  }

  async getEmployeeDocuments(employeeId) {
    return await this.request(`/documents/employee/${employeeId}`);
  }

  async deleteDocument(docId) {
    return await this.request(`/documents/${docId}`, { method: 'DELETE' });
  }

  getDocumentDownloadUrl(docId) {
    return `${API_BASE}/documents/${docId}/download`;
  }

  getAccessToken() {
    return this.token || localStorage.getItem('access_token');
  }

  // --- Notification Endpoints ---
  async getNotifications() {
    return await this.request('/notifications');
  }

  async markNotificationRead(notifId) {
    return await this.request(`/notifications/${notifId}/read`, { method: 'PATCH' });
  }

  async markAllNotificationsRead() {
    return await this.request('/notifications/mark-all-read', { method: 'POST' });
  }
}

const api = new ApiClient();
