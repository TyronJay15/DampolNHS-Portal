// A safe file name such as "Grades-Ana-Reyes-2025-2026-All-terms".
export function pdfFileName(...parts) {
  return parts
    .filter(Boolean)
    .join(' ')
    .replace(/[^A-Za-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
