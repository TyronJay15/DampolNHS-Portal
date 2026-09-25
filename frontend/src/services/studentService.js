import { apiRequest } from './api';

export function fetchStudentMe() {
  return apiRequest('/students/me/', { auth: true });
}

export function updateStudentMe(payload) {
  return apiRequest('/students/me/', { method: 'PATCH', body: payload, auth: true });
}

export function fetchStudentGrades() {
  return apiRequest('/grades/me/', { auth: true });
}

export function fetchNotifications() {
  return apiRequest('/notifications/', { auth: true });
}

export function markNotificationRead(id) {
  return apiRequest(`/notifications/${id}/read/`, { method: 'POST', auth: true });
}

export function markAllNotificationsRead() {
  return apiRequest('/notifications/read-all/', { method: 'POST', auth: true });
}
