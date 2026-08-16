/**
 * ==============================================================================
 * StaffSync 360 - Enterprise API Client Layer
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
    this.isRefreshing = false;
    this.refreshSubscribers = [];
  }

  setSession(accessToken, refreshToken, user) {
    this.token = accessToken;
    if (refreshToken) {
      this.refreshToken = refreshToken;
      localStorage.setItem('refresh_token', refreshToken);
    }
    this.user = user;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user_info', JSON.stringify(user));
  }

  clearSession() {
    this.token = null;
    this.refreshToken = null;
    this.user = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
  }

  onRefreshed(token) {
    this.refreshSubscribers.map(cb => cb(token));
    this.refreshSubscribers = [];
  }

  subscribeTokenRefresh(cb) {
    this.refreshSubscribers.push(cb);
  }

  async refreshAccessToken() {
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
      this.setSession(data.access_token, data.refresh_token, data.user);
      return data.access_token;
    } catch (err) {
      this.clearSession();
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw err;
    }
  }

  async request(endpoint, options = {}, isRetry = false) {
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

      // Handle 401 Unauthorized with automatic silent token refresh
      if (response.status === 401) {
        if (endpoint.startsWith('/auth/login')) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Incorrect Employee ID or password');
        }

        if (endpoint.startsWith('/auth/refresh') || isRetry) {
          this.clearSession();
          window.dispatchEvent(new Event('auth:unauthorized'));
          throw new Error('Session expired. Please sign in again.');
        }

        // Silent token refresh flow
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
  async login(employee_id, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ employee_id: parseInt(employee_id), password })
    });
    this.setSession(res.access_token, res.refresh_token, res.user);
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
  async clockIn(notes = '') {
    return await this.request('/attendance/clock-in', {
      method: 'POST',
      body: JSON.stringify({ notes })
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
    const token = this.getAccessToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${this.baseUrl}/documents/upload`, {
      method: 'POST',
      headers,
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
    return `${this.baseUrl}/documents/${docId}/download`;
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
