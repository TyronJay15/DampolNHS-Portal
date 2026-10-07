// Small display helpers for the guidance screens. Wording only; every decision is made by the server.

export const LABELS = {
  strong: { symbol: '✓', text: 'Strong Match' },
  good: { symbol: '◐', text: 'Good Match' },
  possible: { symbol: '○', text: 'Possible Match' },
  limited: { symbol: '△', text: 'Limited Evidence' },
};

export const INTEREST_WORDS = { high: 'High', medium: 'Medium', low: 'Low', not_assessed: 'Not assessed' };

// 92.00 -> "92", 86.67 -> "86.67"
export function grade(value) {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? String(Number(number.toFixed(2))) : String(value);
}

// A grade on the 60-100 band as a bar width, so differences between good grades stay visible.
export function gradeWidth(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(4, Math.min(100, ((number - 60) / 40) * 100));
}

export function scoreWidth(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(4, Math.min(100, ((number - 1) / 4) * 100));
}

export function strandText(strand) {
  if (!strand?.context) return '';
  const group = strand.group || 'Your strand';
  return strand.context === 'typical' ? `${group} · typical pathway` : `${group} · different pathway`;
}

export function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}
