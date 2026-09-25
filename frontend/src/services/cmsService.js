import { apiRequest } from './api';

export function fetchCms() {
  return apiRequest('/cms/content/');
}

export function saveCmsDocument(document, payload) {
  return apiRequest('/cms/content/', {
    method: 'PATCH',
    auth: true,
    body: { document, payload },
  });
}

export function fetchAnnouncementsAdmin() {
  return apiRequest('/announcements/', { auth: true }).then((data) =>
    Array.isArray(data) ? data : data.results || []
  );
}

export function createAnnouncement(payload) {
  return apiRequest('/announcements/', { method: 'POST', auth: true, body: payload });
}

export function updateAnnouncement(id, payload) {
  return apiRequest(`/announcements/${id}/`, { method: 'PATCH', auth: true, body: payload });
}

export function deleteAnnouncement(id) {
  return apiRequest(`/announcements/${id}/`, { method: 'DELETE', auth: true });
}

export function uploadCmsPhoto(file) {
  const body = new FormData();
  body.append('file', file);
  return apiRequest('/cms/media/', { method: 'POST', auth: true, body });
}

export function deleteCmsPhoto(url) {
  return apiRequest('/cms/media/', { method: 'DELETE', auth: true, body: { url } });
}

export function fetchAdminPrograms() {
  return apiRequest('/admin/programs/', { auth: true });
}

export function saveAdminProgram(id, payload) {
  return apiRequest(`/admin/programs/${id}/`, { method: 'PATCH', auth: true, body: payload });
}

export function createAdminProgram(payload) {
  return apiRequest('/admin/programs/', { method: 'POST', auth: true, body: payload });
}

export function createAdminSubject(payload) {
  return apiRequest('/admin/subjects/', { method: 'POST', auth: true, body: payload });
}
