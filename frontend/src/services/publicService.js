import { apiRequest } from './api';

export function fetchPrograms() {
  return apiRequest('/programs/');
}

export function fetchCms() {
  return apiRequest('/cms/content/');
}

export function fetchAnnouncements(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/announcements/${query ? `?${query}` : ''}`);
}

export function fetchUpcomingEvents() {
  return fetchAnnouncements({ kind: 'event', upcoming: 1 });
}

export function askChatbot(question) {
  return apiRequest('/chatbot/', { method: 'POST', body: { question } });
}
