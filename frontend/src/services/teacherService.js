import { apiRequest } from './api';

export function fetchTeacherAssignments() {
  return apiRequest('/teachers/assignments/', { auth: true });
}

export function fetchClassGrades(assignmentId, termId) {
  return apiRequest(`/grades/class/?assignment=${assignmentId}&term=${termId}`, { auth: true });
}

export function encodeGrade({ assignment, term, student, score }) {
  return apiRequest('/grades/encode/', {
    method: 'POST',
    auth: true,
    body: { assignment, term, student, score },
  });
}

export function submitClassGrades(assignment, term) {
  return apiRequest('/grades/submit/', {
    method: 'POST',
    auth: true,
    body: { assignment, term },
  });
}

export function fetchTerms(schoolYearId) {
  return apiRequest(`/terms/?school_year=${schoolYearId}`, { auth: true }).then((data) =>
    Array.isArray(data) ? data : data.results || []
  );
}

export function fetchAdvisory(assignmentId, termId) {
  return apiRequest(`/grades/advisory/?assignment=${assignmentId}&term=${termId}`, { auth: true });
}

export function showAdvisoryGrades(assignment, term, student) {
  return apiRequest('/grades/show/', { method: 'POST', auth: true, body: { assignment, term, student } });
}

export function hideAdvisoryGrades(assignment, term, student) {
  return apiRequest('/grades/hide/', { method: 'POST', auth: true, body: { assignment, term, student } });
}

export function showReadyCards(assignment, term) {
  return apiRequest('/grades/show-ready/', { method: 'POST', auth: true, body: { assignment, term } });
}

export function requestCorrection(payload) {
  return apiRequest('/grades/corrections/', { method: 'POST', auth: true, body: payload });
}

export function fetchGradeTimeline({ assignment, term, student }) {
  return apiRequest(`/grades/timeline/?assignment=${assignment}&term=${term}&student=${student}`, { auth: true });
}
