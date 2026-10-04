// Tiny shared flag: the login page starts the post-login overlay, an app-level host renders it.
// The host lives above the routes so the overlay survives the move to the dashboard and fades out over it.
let current = null;
const listeners = new Set();

function emit(next) {
  current = next;
  listeners.forEach((listener) => listener());
}

export function beginPostLogin(role) {
  emit({ role });
}

export function endPostLogin() {
  emit(null);
}

export function subscribePostLogin(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getPostLogin() {
  return current;
}
