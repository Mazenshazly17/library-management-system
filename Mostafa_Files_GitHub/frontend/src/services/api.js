const DEFAULT_API_BASE_URL = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';

function normalizeBaseUrl(url) {
  return String(url || DEFAULT_API_BASE_URL).replace(/\/+$/, '');
}

const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL || window.__LIBRARY_API_BASE_URL__
);

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

function getToken() {
  return localStorage.getItem('library_access_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(`Cannot reach backend API at ${API_BASE_URL}`, 0, null);
  }

  let payload = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await response.json();
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.message;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || JSON.stringify(item)).join(', ')
      : detail || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}

function toQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.append(key, value);
  });
  const text = query.toString();
  return text ? `?${text}` : '';
}

export const api = {
  auth: {
    login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    me: () => request('/auth/me'),
    logout: () => request('/auth/logout', { method: 'POST' }),
  },
  health: () => request('/health'),
  books: {
    list: (params) => request(`/books${toQuery(params)}`),
    get: (id) => request(`/books/${id}`),
    create: (data) => request('/books', { method: 'POST', body: JSON.stringify(cleanPayload(data)) }),
    update: (id, data) => request(`/books/${id}`, { method: 'PUT', body: JSON.stringify(cleanPayload(data)) }),
    remove: (id) => request(`/books/${id}`, { method: 'DELETE' }),
  },
  borrows: {
    list: (params) => request(`/borrows${toQuery(params)}`),
    history: (userId, params) => request(`/borrows/users/${userId}/history${toQuery(params)}`),
    create: (data) => request('/borrows', { method: 'POST', body: JSON.stringify(cleanPayload(data)) }),
    approve: (recordId) => request(`/borrows/${recordId}/approve`, { method: 'POST' }),
    reject: (recordId, data = {}) => request(`/borrows/${recordId}/reject`, { method: 'POST', body: JSON.stringify(cleanPayload(data)) }),
    returnBook: (recordId, data = {}) => request(`/borrows/${recordId}/return`, { method: 'POST', body: JSON.stringify(cleanPayload(data)) }),
    markOverdue: () => request('/borrows/admin/mark-overdue', { method: 'POST' }),
  },
  users: {
    list: (params) => request(`/users${toQuery(params)}`),
    update: (id, data) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(cleanPayload(data)) }),
    remove: (id) => request(`/users/${id}`, { method: 'DELETE' }),
  },
};

function cleanPayload(data) {
  return Object.fromEntries(
    Object.entries(data).filter(([, value]) => value !== '' && value !== null && value !== undefined)
  );
}

export { API_BASE_URL };
