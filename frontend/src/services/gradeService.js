import { apiRequest } from './api';

function printQuery(params) {
  const query = new URLSearchParams();
  ['student', 'school_year', 'term'].forEach((key) => {
    if (params[key]) query.set(key, params[key]);
  });
  const text = query.toString();
  return text ? `?${text}` : '';
}

// Read-only report data for the print pages. The server decides who may read which grades.
export function fetchGradePrint(params = {}) {
  return apiRequest(`/grades/print/${printQuery(params)}`, { auth: true });
}

export function fetchRecordsPrint(params = {}) {
  return apiRequest(`/grades/print/records/${printQuery(params)}`, { auth: true });
}
