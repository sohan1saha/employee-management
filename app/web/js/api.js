/**
 * StaffSync 360 - API Client Layer
 */

const API_BASE = '/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token') || null;
    this.user = JSON.parse(localStorage.getItem('user_info') || 'null');
  }

  setSession(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify(user));
  }

  clearSession() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, { ...options, headers });
      
      if (response.status === 401) {
        const errData = await response.json().catch(() => ({}));
        if (endpoint.startsWith('/auth/login')) {
          throw new Error(errData.detail || 'Incorrect username or password');
        }
        this.clearSession();
        window.dispatchEvent(new Event('auth:unauthorized'));
        throw new Error(errData.detail || 'Session expired. Please log in again.');
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Request failed with status ${response.status}`);
      }

      // Handle raw stream/blob for PDF downloads
      if (response.headers.get('content-type')?.includes('application/pdf')) {
        return await response.blob();
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // Auth Endpoints
  async login(employee_id, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ employee_id: parseInt(employee_id), password })
    });
    this.setSession(res.access_token, res.user);
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

  // Employee Endpoints
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

  // Analytics Endpoints
  async getAnalytics() {
    return await this.request('/analytics/summary');
  }

  // Payroll Endpoints
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

  // Leave Endpoints
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

  // Audit Endpoints
  async getAuditLogs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/audit/logs${query ? '?' + query : ''}`);
  }
}

const api = new ApiClient();
