const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const API_ORIGIN = API_BASE.replace(/\/api\/?$/, '');

export function fileUrl(path) {
  const value = String(path || '');
  if (!value || /^https?:\/\//i.test(value) || !value.startsWith('/media/')) return value;
  return `${API_ORIGIN}${value}`;
}

export function getAccessToken() {
  return localStorage.getItem('accessToken') || '';
}

export function getRefreshToken() {
  return localStorage.getItem('refreshToken') || '';
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem('accessToken', access);
  if (refresh) localStorage.setItem('refreshToken', refresh);
}

export function clearTokens() {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
}

async function parseBody(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export async function apiRequest(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { Accept: 'application/json' };
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  if (body !== undefined && !isForm) {
    headers['Content-Type'] = 'application/json';
  }
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    const error = new Error('Unable to reach the server. Check that the API is running.');
    error.isNetworkError = true;
    throw error;
  }

  const data = await parseBody(response);
  if (!response.ok) {
    const error = new Error(data?.detail || 'Request failed.');
    error.status = response.status;
    error.data = data;
    error.code = data?.code;
    throw error;
  }
  return data;
}
