import { apiRequest } from './api';

export function fetchRegistrations(status = 'pending') {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiRequest(`/admin/registrations/${query}`, { auth: true });
}

export function approveRegistration(id) {
  return apiRequest(`/admin/registrations/${id}/approve/`, { method: 'POST', auth: true, body: {} });
}

export function rejectRegistration(id, reason) {
  return apiRequest(`/admin/registrations/${id}/reject/`, {
    method: 'POST',
    auth: true,
    body: { reason },
  });
}

export function fetchSchoolYears() {
  return apiRequest('/school-years/', { auth: true }).then((data) =>
    Array.isArray(data) ? data : data.results || []
  );
}

export function createSchoolYear(payload) {
  return apiRequest('/school-years/', { method: 'POST', auth: true, body: payload });
}

export function saveSchoolYear(id, payload) {
  return apiRequest(`/school-years/${id}/`, { method: 'PATCH', auth: true, body: payload });
}

export function archiveSchoolYear(id) {
  return apiRequest(`/school-years/${id}/archive/`, { method: 'POST', auth: true, body: {} });
}

export function restoreSchoolYear(id) {
  return apiRequest(`/school-years/${id}/restore/`, { method: 'POST', auth: true, body: {} });
}

export function deleteSchoolYear(id) {
  return apiRequest(`/school-years/${id}/delete/`, { method: 'DELETE', auth: true });
}

export function fetchGradeQueues(termId) {
  return apiRequest(`/grades/queues/?term=${termId}`, { auth: true });
}

export function approveGrades({ term, section, subject }) {
  return apiRequest('/grades/approve/', { method: 'POST', auth: true, body: { term, section, subject } });
}

export function returnGrades({ term, section, subject }) {
  return apiRequest('/grades/return/', { method: 'POST', auth: true, body: { term, section, subject } });
}

export function fetchPlacements() {
  return apiRequest('/admin/placements/', { auth: true });
}

export function savePlacement({ student, section, transfer = false, override_capacity = false, reason = '' }) {
  return apiRequest('/admin/placements/', {
    method: 'POST',
    auth: true,
    body: { student, section, transfer, override_capacity, reason },
  });
}

export function savePlacementsBulk({ section, students, override_capacity = false, reason = '' }) {
  return apiRequest('/admin/placements/bulk/', {
    method: 'POST',
    auth: true,
    body: { section, students, override_capacity, reason },
  });
}

export function fetchTeachers() {
  return apiRequest('/admin/teachers/', { auth: true });
}

export function fetchAssignments() {
  return apiRequest('/admin/assignments/', { auth: true });
}

export function saveAssignment(payload) {
  return apiRequest('/admin/assignments/', { method: 'POST', auth: true, body: payload });
}

export function deleteAssignment(id) {
  return apiRequest(`/admin/assignments/${id}/`, { method: 'DELETE', auth: true });
}

export function restoreAssignment(id) {
  return apiRequest(`/admin/assignments/${id}/`, { method: 'POST', auth: true, body: {} });
}

export function purgeDuty(id) {
  return apiRequest(`/admin/assignments/${id}/purge/`, { method: 'POST', auth: true, body: {} });
}

export function fetchSections(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value);
  });
  const suffix = query.toString() ? `?${query}` : '';
  return apiRequest(`/sections/${suffix}`, { auth: true }).then((data) =>
    Array.isArray(data) ? data : data.results || []
  );
}

export function createSection(payload) {
  return apiRequest('/sections/', { method: 'POST', auth: true, body: payload });
}

export function saveSection(id, payload) {
  return apiRequest(`/sections/${id}/`, { method: 'PATCH', auth: true, body: payload });
}

export function deleteSection(id) {
  return apiRequest(`/sections/${id}/`, { method: 'DELETE', auth: true });
}

export function fetchSectionPurgeSummary(id) {
  return apiRequest(`/sections/${id}/purge/summary/`, { auth: true });
}

export function purgeSection(id, payload = {}) {
  return apiRequest(`/sections/${id}/purge/`, { method: 'POST', auth: true, body: payload });
}

export function fetchSchoolYearPurgeSummary(id) {
  return apiRequest(`/school-years/${id}/purge/summary/`, { auth: true });
}

export function purgeSchoolYear(id, payload = {}) {
  return apiRequest(`/school-years/${id}/purge/`, { method: 'POST', auth: true, body: payload });
}

export function fetchSectionRoster(id) {
  return apiRequest(`/sections/${id}/roster/`, { auth: true });
}

export function archiveSection(id) {
  return apiRequest(`/sections/${id}/archive/`, { method: 'POST', auth: true, body: {} });
}

export function restoreSection(id) {
  return apiRequest(`/sections/${id}/restore/`, { method: 'POST', auth: true, body: {} });
}

export function fetchSectionDetail(id) {
  return apiRequest(`/sections/${id}/detail/`, { auth: true });
}

export function activateSection(id, payload = {}) {
  return apiRequest(`/sections/${id}/activate/`, { method: 'POST', auth: true, body: payload });
}

export function approveTeacherGrades({ term, teacher }) {
  return apiRequest('/grades/approve/teacher/', { method: 'POST', auth: true, body: { term, teacher } });
}

export function approveAllGrades(term) {
  return apiRequest('/grades/approve/all/', { method: 'POST', auth: true, body: { term } });
}

export function fetchArchive(kind, schoolYear) {
  const query = new URLSearchParams({ kind });
  if (schoolYear) query.set('school_year', schoolYear);
  return apiRequest(`/admin/archive/?${query}`, { auth: true });
}

export function fetchAccountArchive(kind = 'students') {
  return apiRequest(`/admin/account-archive/?kind=${encodeURIComponent(kind)}`, { auth: true });
}

export function fetchSubjects(program) {
  const query = program ? `?program=${encodeURIComponent(program)}` : '';
  return apiRequest(`/subjects/${query}`, { auth: true }).then((data) =>
    Array.isArray(data) ? data : data.results || []
  );
}

export function fetchPrograms() {
  return apiRequest('/programs/').then((data) => (Array.isArray(data) ? data : data.results || []));
}

export function fetchStaffAccounts() {
  return apiRequest('/admin/staff/', { auth: true });
}

export function createStaffAccount(payload) {
  return apiRequest('/admin/staff/', { method: 'POST', auth: true, body: payload });
}

export function resendStaffActivation(id) {
  return apiRequest(`/admin/staff/${id}/resend-activation/`, { method: 'POST', auth: true, body: {} });
}

export function deactivateAccount(id, reason = '') {
  return apiRequest(`/admin/accounts/${id}/deactivate/`, { method: 'POST', auth: true, body: { reason } });
}

export function reactivateAccount(id) {
  return apiRequest(`/admin/accounts/${id}/reactivate/`, { method: 'POST', auth: true, body: {} });
}

export function restoreRejectedToPending(id) {
  return apiRequest(`/admin/accounts/${id}/restore-pending/`, { method: 'POST', auth: true, body: {} });
}

export function removeAccount(id) {
  return apiRequest(`/admin/accounts/${id}/remove/`, { method: 'POST', auth: true, body: {} });
}

export function fetchEncodeWindowHistory(schoolYearId) {
  const query = schoolYearId ? `?school_year=${schoolYearId}` : '';
  return apiRequest(`/terms/window-history/${query}`, { auth: true });
}

export function fetchAuditLogs() {
  return apiRequest('/audit-logs/', { auth: true });
}

export function fetchGrade11Forecast() {
  return apiRequest('/admin/forecast/', { auth: true });
}

export function fetchAssistantStats() {
  return apiRequest('/ml/assistant/', { auth: true });
}

export function saveTermDeadline(termId, payload) {
  return apiRequest(`/terms/${termId}/`, { method: 'PATCH', auth: true, body: payload });
}

export function fetchGradeHistory() {
  return apiRequest('/grades/history/', { auth: true });
}

export function fetchGradeReport(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString() ? `?${query}` : '';
  return apiRequest(`/grades/report/${suffix}`, { auth: true });
}

export function fetchCorrections(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiRequest(`/grades/corrections/${query}`, { auth: true });
}

export function reviewCorrection(id, payload) {
  return apiRequest(`/grades/corrections/${id}/review/`, { method: 'POST', auth: true, body: payload });
}
