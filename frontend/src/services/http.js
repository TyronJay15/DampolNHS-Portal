// Shared HTTP basics for api.js and session.js: the API address, response parsing and error objects.

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.DEV ? 'http://localhost:8000/api' : '');
if (!API_BASE) {
  throw new Error('VITE_API_BASE_URL is missing from the production build.');
}
export const API_ORIGIN = API_BASE.replace(/\/api\/?$/, '');

export async function parseBody(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export function requestError(response, data) {
  const error = new Error(data?.detail || 'Request failed.');
  error.status = response.status;
  error.data = data;
  error.code = data?.code;
  return error;
}

export function networkError() {
  const error = new Error('Unable to reach the server. Check that the API is running.');
  error.isNetworkError = true;
  return error;
}
