const LIMIT = 140;

export function textPreview(value, limit = LIMIT) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= limit) return { text, isLong: false };
  const slice = text.slice(0, limit);
  const cut = slice.lastIndexOf(' ');
  return { text: `${(cut > 80 ? slice.slice(0, cut) : slice).trim()}…`, isLong: true };
}

export function formatPostedOn(value) {
  if (!value) return '';
  return new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

export function formatEventWhen(row, { long = false } = {}) {
  if (!row?.event_date) return '';
  const opts = long
    ? { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric' }
    : { month: 'short', day: 'numeric' };
  const start = new Date(`${row.event_date}T00:00:00`);
  const startLabel = start.toLocaleDateString(undefined, opts);
  if (!row.event_end_date || row.event_end_date === row.event_date) return startLabel;
  const end = new Date(`${row.event_end_date}T00:00:00`);
  return `${startLabel}–${end.toLocaleDateString(undefined, opts)}`;
}
