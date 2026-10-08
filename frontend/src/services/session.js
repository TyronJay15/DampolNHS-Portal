// The sign-in, held so that a script on the page can never read a credential that outlives a few minutes.
//
// - The access token lives only in this module's memory: never in localStorage, sessionStorage or the URL.
// - The refresh token lives in an HttpOnly cookie that JavaScript cannot read; the browser sends it to
//   /api/auth/ only. A page reload restores the sign-in by refreshing (restore()).
// - Login, refresh and logout send the CSRF token, which is fetched from /api/auth/csrf/ and kept in memory.
// - One refresh at a time, across every open tab (Web Locks), because each refresh token works once.
// - 30 minutes without activity in any tab signs out everywhere. The open tab's timer enforces it; the server
//   enforces it too when no tab is open or the computer was asleep (no refresh for 30 minutes).
// - Only a "last activity" time stamp is shared between tabs through localStorage. It is not a credential.

import { API_BASE, networkError, parseBody, requestError } from './http';

const LOCK = 'dampol-auth-refresh';
const CHANNEL = 'dampol-auth';
const ACTIVITY_KEY = 'dampol.lastActivity';
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel', 'touchstart'];
const IDLE_MS = 30 * 60 * 1000;
const RENEW_GAP_MS = 5 * 60 * 1000; // an active person renews at most this often, so the server sees the activity
const EXPIRY_MARGIN_MS = 60 * 1000;
const ACTIVITY_WRITE_MS = 15 * 1000;
const IDLE_CHECK_MS = 30 * 1000;

let access = '';
let accessExpires = 0;
let lastRefresh = 0;
let lastActivity = Date.now();
let lastActivityWrite = 0;
let csrfToken = '';
let inFlight = null;
let idleTimer = null;
let onEnd = () => {};

const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL) : null;

// ---- Activity ----

function noteActivity() {
  lastActivity = Date.now();
  if (lastActivity - lastActivityWrite < ACTIVITY_WRITE_MS) return;
  lastActivityWrite = lastActivity;
  try {
    localStorage.setItem(ACTIVITY_KEY, String(lastActivity));
  } catch {
    // Storage may be blocked (private mode); this tab still tracks its own activity.
  }
}

function latestActivity() {
  let shared = 0;
  try {
    shared = Number(localStorage.getItem(ACTIVITY_KEY)) || 0;
  } catch {
    shared = 0;
  }
  return Math.max(lastActivity, shared);
}

if (typeof window !== 'undefined') {
  ACTIVITY_EVENTS.forEach((name) => window.addEventListener(name, noteActivity, { passive: true }));
}

function watchIdle() {
  if (idleTimer) return;
  idleTimer = window.setInterval(() => {
    if (access && Date.now() - latestActivity() >= IDLE_MS) {
      signOut('idle').finally(() => onEnd('idle'));
    }
  }, IDLE_CHECK_MS);
}

// ---- State ----

function expiryOf(token) {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = part + '='.repeat((4 - (part.length % 4)) % 4);
    return JSON.parse(atob(padded)).exp * 1000;
  } catch {
    return 0;
  }
}

function accept(data) {
  access = data.access;
  accessExpires = expiryOf(access);
  lastRefresh = Date.now();
  watchIdle();
  return data.user;
}

function clear() {
  access = '';
  accessExpires = 0;
  lastRefresh = 0;
  if (idleTimer) {
    window.clearInterval(idleTimer);
    idleTimer = null;
  }
}

function ended(reason) {
  const wasSignedIn = Boolean(access);
  clear();
  if (wasSignedIn) {
    channel?.postMessage({ type: 'signed-out', reason });
    onEnd(reason);
  }
}

// Another tab signed out: this one follows, with the same reason when there was one.
channel?.addEventListener('message', (event) => {
  if (event.data?.type === 'signed-out' && access) {
    clear();
    onEnd(event.data.reason || 'elsewhere');
  }
});

/** The AuthContext learns here when the sign-in ends on its own: 'idle', 'ended' or 'elsewhere'. */
export function onSessionEnd(listener) {
  onEnd = listener;
}

// ---- Requests to the cookie endpoints ----

async function csrf(force = false) {
  if (csrfToken && !force) return csrfToken;
  let response;
  try {
    response = await fetch(`${API_BASE}/auth/csrf/`, { credentials: 'include', headers: { Accept: 'application/json' } });
  } catch {
    throw networkError();
  }
  const data = await parseBody(response);
  if (!response.ok) throw requestError(response, data);
  csrfToken = data.csrf_token;
  return csrfToken;
}

async function authPost(path, body, retry = true) {
  const token = await csrf();
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': token },
      body: JSON.stringify(body ?? {}),
    });
  } catch {
    throw networkError();
  }
  const data = await parseBody(response);
  if (response.status === 403 && data?.code === 'csrf_failed' && retry) {
    await csrf(true);
    return authPost(path, body, false);
  }
  return { response, data };
}

async function expectOk(path, body) {
  const { response, data } = await authPost(path, body);
  if (!response.ok) throw requestError(response, data);
  return data;
}

// ---- Signing in ----

/** Returns { user } after the password and reCAPTCHA are accepted. */
export async function signIn(credentials) {
  const data = await expectOk('/auth/login/', credentials);
  noteActivity();
  return { user: accept(data) };
}

// ---- Keeping the sign-in ----

function withLock(task) {
  return navigator.locks?.request ? navigator.locks.request(LOCK, task) : task();
}

function pause(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function refreshOnce(attempt = 0) {
  const { response, data } = await authPost('/auth/refresh/');
  if (response.ok) return accept(data);
  if (response.status === 409 && attempt < 2) {
    await pause(400);
    return refreshOnce(attempt + 1);
  }
  if (response.status === 401) {
    ended('ended');
    return null;
  }
  throw requestError(response, data);
}

/** Exchange the refresh cookie for a new access token. Returns the user, or null when the sign-in has ended. */
export function refresh() {
  if (!inFlight) {
    inFlight = withLock(() => refreshOnce()).finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}

/** After a page load: the signed-in user, or null. */
export async function restore() {
  noteActivity();
  try {
    return await refresh();
  } catch {
    return null;
  }
}

/** The access token for an API call, renewed first when it is about to expire, and every few minutes while the
 * person is active so the server's idle clock follows real use. */
export async function accessToken() {
  if (!access) return '';
  const now = Date.now();
  const active = latestActivity() > lastRefresh;
  const expiring = accessExpires - now < EXPIRY_MARGIN_MS;
  if (expiring || (active && now - lastRefresh > RENEW_GAP_MS)) {
    try {
      await refresh();
    } catch {
      // The network may be down; the current token is still tried.
    }
  }
  return access;
}

/** The server said the sign-in ended (signed out elsewhere, archived, password changed). */
export function sessionEnded() {
  ended('ended');
}

/** Sign out on the server and here, in every tab. Returns false when the server could not be told. */
export async function signOut(reason = '') {
  let confirmed = true;
  try {
    const { response } = await authPost('/auth/logout/');
    confirmed = response.ok;
  } catch {
    confirmed = false;
  }
  const wasSignedIn = Boolean(access);
  clear();
  if (wasSignedIn) channel?.postMessage({ type: 'signed-out', reason });
  return confirmed;
}
