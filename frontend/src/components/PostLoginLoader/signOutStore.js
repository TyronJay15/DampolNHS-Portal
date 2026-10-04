// Tiny shared flag for the sign-out overlay, like postLoginStore: the dashboard starts it, an app-level host
// renders it, so it survives the move to the login page and fades out over it.
//   null                        no overlay
//   { done: false }             signing out
//   { done: true, offline }     tokens cleared; offline when the server could not be told
let current = null;
const listeners = new Set();

function emit(next) {
  current = next;
  listeners.forEach((listener) => listener());
}

export function beginSignOut() {
  emit({ done: false, offline: false });
}

export function finishSignOut({ offline }) {
  emit({ done: true, offline });
}

export function endSignOut() {
  emit(null);
}

export function isSigningOut() {
  return current !== null;
}

export function subscribeSignOut(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSignOut() {
  return current;
}
