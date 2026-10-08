import { apiRequest } from './api';

export function fetchPrograms(gradeLevel = '') {
  const query = gradeLevel ? `?grade_level=${encodeURIComponent(gradeLevel)}` : '';
  return apiRequest(`/programs/${query}`);
}

export function fetchCms() {
  return apiRequest('/cms/content/');
}

// surface: 'website' or 'dashboard'. The server returns only published posts whose "Publish to" includes it.
export function fetchAnnouncements(params = {}, { auth = false } = {}) {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/announcements/${query ? `?${query}` : ''}`, { auth });
}

/** Upcoming events for the public website: "Website" and "Both" posts. */
export function fetchUpcomingEvents() {
  return fetchAnnouncements({ kind: 'event', upcoming: 1, surface: 'website' });
}

/** Upcoming events for the signed-in dashboards: "Dashboard" and "Both" posts. */
export function fetchDashboardEvents() {
  return fetchAnnouncements({ kind: 'event', upcoming: 1, surface: 'dashboard' }, { auth: true });
}

/** News for the signed-in dashboards' Announcements section: "Dashboard" and "Both" posts, newest first. */
export function fetchDashboardNews() {
  return fetchAnnouncements({ kind: 'news', surface: 'dashboard' }, { auth: true });
}

function asList(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

/** News plus upcoming events, for the public site. Events come first so a published date is not hidden behind news. */
export async function fetchPublicBulletin() {
  const [news, events] = await Promise.all([
    fetchAnnouncements({ kind: 'news', surface: 'website' }),
    fetchUpcomingEvents(),
  ]);
  const seen = new Set();
  return [...asList(events), ...asList(news)].filter((row) => {
    if (seen.has(row.id)) return false;
    seen.add(row.id);
    return true;
  });
}

// Sends the in-memory access token when someone is signed in, so the server can answer staff-only live
// questions for the roles allowed to see them. Signed out, no token is sent and the public answers still work.
export function askChatbot(question) {
  return apiRequest('/chatbot/', { method: 'POST', auth: true, body: { question } });
}
