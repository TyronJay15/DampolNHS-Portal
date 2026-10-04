import { apiRequest } from './api';

export function fetchAccessOverview() {
  return apiRequest('/access/overview/', { auth: true });
}

export function fetchAccessTags() {
  return apiRequest('/access/tags/', { auth: true });
}

export function grantAccessTag(payload) {
  return apiRequest('/access/tags/', { method: 'POST', auth: true, body: payload });
}

export function closeAccessTag(id, reason) {
  return apiRequest(`/access/tags/${id}/close/`, { method: 'POST', auth: true, body: { reason } });
}

// box: inbox (waiting for me), mine (what I submitted), decided (history)
export function fetchAccessRequests(box) {
  return apiRequest(`/access/requests/?box=${encodeURIComponent(box)}`, { auth: true });
}

export function submitAccessRequest({ activity, payload, note }) {
  return apiRequest('/access/requests/', { method: 'POST', auth: true, body: { activity, payload, note } });
}

export function withdrawAccessRequest(id) {
  return apiRequest(`/access/requests/${id}/withdraw/`, { method: 'POST', auth: true, body: {} });
}

export function decideAccessRequest(id, { approve, note }) {
  return apiRequest(`/access/requests/${id}/decide/`, { method: 'POST', auth: true, body: { approve, note } });
}
