import { apiRequest } from './api';

// Student: every call reads the signed-in student's own data; no student id is ever sent.
export function fetchGuidance() {
  return apiRequest('/guidance/me/', { auth: true });
}

export function giveConsent({ kind, noticeVersion, guardianConfirmed }) {
  return apiRequest('/guidance/me/consent/', {
    method: 'POST',
    auth: true,
    body: { kind, notice_version: noticeVersion, guardian_confirmed: guardianConfirmed },
  });
}

export function withdrawConsent(kind) {
  return apiRequest('/guidance/me/consent/withdraw/', { method: 'POST', auth: true, body: { kind } });
}

export function fetchAssessment() {
  return apiRequest('/guidance/me/assessment/', { auth: true });
}

export function startAssessment() {
  return apiRequest('/guidance/me/assessment/start/', { method: 'POST', auth: true });
}

export function saveAnswer(question, value) {
  return apiRequest('/guidance/me/assessment/answer/', { method: 'PUT', auth: true, body: { question, value } });
}

export function completeAssessment() {
  return apiRequest('/guidance/me/assessment/complete/', { method: 'POST', auth: true });
}

export function deleteGuidanceData() {
  return apiRequest('/guidance/me/assessment/', { method: 'DELETE', auth: true });
}

export function fetchCatalog(family = '') {
  const query = family ? `?family=${encodeURIComponent(family)}` : '';
  return apiRequest(`/guidance/programs/${query}`, { auth: true });
}

export function fetchProgramFit(code) {
  return apiRequest(`/guidance/me/programs/${encodeURIComponent(code)}/`, { auth: true });
}

export function fetchComparison(codes) {
  return apiRequest(`/guidance/me/compare/?programs=${codes.map(encodeURIComponent).join(',')}`, { auth: true });
}

// Adviser: always through the adviser's own assignment; the server checks the student belongs to it.
export function fetchAdvisoryGuidance(assignmentId) {
  return apiRequest(`/guidance/advisory/${assignmentId}/`, { auth: true });
}

export function fetchAdvisee(assignmentId, studentId) {
  return apiRequest(`/guidance/advisory/${assignmentId}/students/${studentId}/`, { auth: true });
}

export function addAdviserNote(assignmentId, studentId, body) {
  return apiRequest(`/guidance/advisory/${assignmentId}/students/${studentId}/notes/`, {
    method: 'POST',
    auth: true,
    body: { body },
  });
}

export function addAdviserRecommendation(assignmentId, studentId, payload) {
  return apiRequest(`/guidance/advisory/${assignmentId}/students/${studentId}/recommendation/`, {
    method: 'POST',
    auth: true,
    body: payload,
  });
}

export function recordOutcome(assignmentId, studentId, program) {
  return apiRequest(`/guidance/advisory/${assignmentId}/students/${studentId}/outcome/`, {
    method: 'POST',
    auth: true,
    body: { program },
  });
}

// Expert ratings: form data only; ratings are submitted as access requests the Admin approves.
export function fetchRatingForm() {
  return apiRequest('/guidance/ratings/', { auth: true });
}

// Admin.
export function fetchGuidanceCatalog() {
  return apiRequest('/guidance/admin/catalog/', { auth: true });
}

export function createFamily(payload) {
  return apiRequest('/guidance/admin/families/', { method: 'POST', auth: true, body: payload });
}

export function updateFamily(code, payload) {
  return apiRequest(`/guidance/admin/families/${encodeURIComponent(code)}/`, { method: 'PATCH', auth: true, body: payload });
}

export function saveInterestMap(map) {
  return apiRequest('/guidance/admin/interest-map/', { method: 'PUT', auth: true, body: { map } });
}

export function createProgram(payload) {
  return apiRequest('/guidance/admin/programs/', { method: 'POST', auth: true, body: payload });
}

export function fetchAdminProgram(code) {
  return apiRequest(`/guidance/admin/programs/${encodeURIComponent(code)}/`, { auth: true });
}

export function updateProgram(code, payload) {
  return apiRequest(`/guidance/admin/programs/${encodeURIComponent(code)}/`, { method: 'PATCH', auth: true, body: payload });
}

export function programAction(code, action, payload = {}) {
  return apiRequest(`/guidance/admin/programs/${encodeURIComponent(code)}/${action}/`, {
    method: 'POST',
    auth: true,
    body: payload,
  });
}

export function importPrograms(file, commit) {
  const form = new FormData();
  form.append('file', file);
  form.append('commit', commit ? 'true' : 'false');
  return apiRequest('/guidance/admin/programs/import/', { method: 'POST', auth: true, body: form });
}

export function fetchInstruments() {
  return apiRequest('/guidance/admin/instruments/', { auth: true });
}

export function activateInstrument(id) {
  return apiRequest(`/guidance/admin/instruments/${id}/activate/`, {
    method: 'POST',
    auth: true,
    body: { license_confirmed: true },
  });
}

export function fetchOutcomes(status) {
  return apiRequest(`/guidance/admin/outcomes/?status=${encodeURIComponent(status)}`, { auth: true });
}

export function validateOutcome(id) {
  return apiRequest(`/guidance/admin/outcomes/${id}/validate/`, { method: 'POST', auth: true });
}

export function fetchRecommenderStatus() {
  return apiRequest('/guidance/admin/recommender/', { auth: true });
}

export function fetchRecommenderConfig() {
  return apiRequest('/guidance/admin/config/', { auth: true });
}

export function saveRecommenderConfig(payload) {
  return apiRequest('/guidance/admin/config/', { method: 'POST', auth: true, body: payload });
}

export function activateRecommenderConfig(id) {
  return apiRequest(`/guidance/admin/config/${id}/activate/`, { method: 'POST', auth: true });
}
