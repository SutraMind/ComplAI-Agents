import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response.data; // Return only the data part
  },
  (error) => {
    console.error('API Response Error:', error);
    
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error || error.response.data?.message || 'Server error';
      throw new Error(`${error.response.status}: ${message}`);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Network error: Unable to connect to server');
    } else {
      // Something else happened
      throw new Error(`Request error: ${error.message}`);
    }
  }
);

const apiService = {
  // Reports
  async getReports() {
    return await api.get('/reports');
  },

  async getReport(reportId) {
    return await api.get(`/reports/${reportId}`);
  },

  async createReport(filename, content) {
    return await api.post('/reports', { filename, content });
  },

  async updateReport(reportId, content) {
    return await api.put(`/reports/${reportId}`, { content });
  },

  async deleteReport(reportId) {
    return await api.delete(`/reports/${reportId}`);
  },

  // Comments
  async getReportComments(reportId) {
    return await api.get(`/reports/${reportId}/comments`);
  },

  async createComment(reportId, commentData) {
    return await api.post(`/reports/${reportId}/comments`, commentData);
  },

  async updateComment(commentId, commentText) {
    return await api.put(`/comments/${commentId}`, { comment_text: commentText });
  },

  async deleteComment(commentId) {
    return await api.delete(`/comments/${commentId}`);
  },

  async getComment(commentId) {
    return await api.get(`/comments/${commentId}`);
  },

  // Summaries
  async generateSummary(reportId) {
    return await api.post(`/reports/${reportId}/summary`);
  },

  async getSummary(reportId) {
    return await api.get(`/reports/${reportId}/summary`);
  },

  async updateSummary(reportId) {
    return await api.put(`/reports/${reportId}/summary`);
  },

  async deleteSummary(reportId) {
    return await api.delete(`/reports/${reportId}/summary`);
  },

  async exportSummary(reportId) {
    return await api.get(`/reports/${reportId}/summary/export`);
  },

  // Feedback
  async saveFeedbackFile(reportId) {
    return await api.post(`/reports/${reportId}/feedback`);
  },

  // Health check
  async healthCheck() {
    return await api.get('/health');
  },
};

export default apiService;