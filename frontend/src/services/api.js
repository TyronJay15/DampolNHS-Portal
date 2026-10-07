import { API_BASE, API_ORIGIN, networkError, parseBody, requestError } from './http';
import { accessToken, refresh, sessionEnded } from './session';

// The server's answers that mean the sign-in itself is over (not just this token).
const SESSION_GONE = new Set(['session_ended', 'account_unavailable']);

export function fileUrl(path) {
  const value = String(path || '');
  if (!value || /^https?:\/\//i.test(value) || !value.startsWith('/media/')) return value;
  return `${API_ORIGIN}${value}`;
}

async function send(path, { method, body, isForm, token }) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw networkError();
  }
}

export async function apiRequest(path, { method = 'GET', body, auth = false } = {}) {
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  let response = await send(path, { method, body, isForm, token: auth ? await accessToken() : '' });
  let data = await parseBody(response);

  if (auth && response.status === 401) {
    if (SESSION_GONE.has(data?.code)) {
      sessionEnded();
    } else {
      // The access token expired between the check and the request: renew once and repeat it.
      const user = await refresh().catch(() => null);
      if (user) {
        response = await send(path, { method, body, isForm, token: await accessToken() });
        data = await parseBody(response);
      }
    }
  }

  if (!response.ok) throw requestError(response, data);
  return data;
}
