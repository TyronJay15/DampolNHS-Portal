// The programs a student picked to compare, kept for this browser tab only. A convenience: losing it is harmless.
const KEY = 'guidance-compare';
export const MAX_COMPARE = 3;

export function readCompare() {
  try {
    const value = JSON.parse(sessionStorage.getItem(KEY) || '[]');
    return Array.isArray(value) ? value.filter((code) => typeof code === 'string').slice(0, MAX_COMPARE) : [];
  } catch {
    return [];
  }
}

export function writeCompare(codes) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(codes.slice(0, MAX_COMPARE)));
  } catch {
    // Storage can be unavailable (private mode); the selection then lasts only on this page.
  }
}
