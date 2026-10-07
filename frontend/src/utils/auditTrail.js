const EVENT_FAMILIES = [
  { value: 'all', label: 'All' },
  { value: 'accounts', label: 'Accounts' },
  { value: 'school', label: 'School' },
  { value: 'assignments', label: 'Assignments' },
  { value: 'placement', label: 'Placement' },
  { value: 'grades', label: 'Grades' },
  { value: 'announcements', label: 'Announcements' },
  { value: 'access', label: 'Access' },
  { value: 'guidance', label: 'College recommendation' },
  { value: 'security', label: 'Security' },
];

// College recommendation records audit events but sends no notifications, so its tab is left out here.
export const NOTIFICATION_FILTERS = EVENT_FAMILIES.filter((row) => row.value !== 'guidance');

const ACTION_LABELS = {
  register: 'Registration submitted',
  login: 'Signed in',
  password_otp_requested: 'Password code sent',
  password_change: 'Password changed',
  account_approved: 'Student approved',
  registrations_bulk_approved: 'Students approved together',
  registration_emails_resent: 'Registration emails resent',
  account_rejected: 'Student rejected',
  account_archived: 'Account archived',
  account_reactivated: 'Account reactivated',
  account_removed: 'Account removed',
  registration_restored_pending: 'Registration reopened',
  student_profile_updated: 'Student profile updated',
  student_gender_set: 'Student gender updated',
  staff_created: 'Staff created',
  staff_activated: 'Staff activated',
  staff_activation_resent: 'Activation resent',
  school_year_created: 'School year opened',
  school_year_archived: 'School year archived',
  school_year_restored: 'School year restored',
  school_year_deleted: 'School year deleted',
  school_year_hard_deleted: 'School year hard deleted',
  deadline_set: 'Encode window set',
  term_plan_saved: 'Term plan saved',
  section_created: 'Section created',
  section_deleted: 'Section deleted',
  section_hard_deleted: 'Section hard deleted',
  section_archived: 'Section archived',
  section_restored: 'Section restored',
  section_activated: 'Section activated',
  section_activated_incomplete: 'Section activated (incomplete)',
  program_created: 'Program created',
  program_updated: 'Program updated',
  model_trained: 'Model retrained',
  retention_rate_changed: 'Retention rate changed',
  adviser_assigned: 'Adviser assigned',
  subject_teacher_assigned: 'Subject teacher assigned',
  assignment_ended: 'Assignment ended',
  assignment_purged: 'Assignment purged',
  student_placed: 'Student placed',
  student_transferred: 'Student transferred',
  grades_submitted: 'Grades submitted',
  grades_approved: 'Grades approved',
  grades_returned: 'Grades returned',
  grades_shown: 'Card shown',
  grades_hidden: 'Card hidden',
  grades_shown_ready: 'Ready cards shown',
  correction_requested: 'Correction requested',
  correction_approved: 'Correction approved',
  correction_rejected: 'Correction rejected',
  cms_save: 'Website saved',
  announcement_published: 'Event published',
  access_tag_granted: 'Access tag granted',
  access_tag_closed: 'Access tag closed',
  access_request_submitted: 'Request submitted',
  access_request_withdrawn: 'Request withdrawn',
  access_request_expired: 'Request expired',
  access_request_approved: 'Request approved and applied',
  access_request_declined: 'Request declined',
  access_request_failed: 'Request could not be applied',
  college_program_added: 'College program added',
  college_program_updated: 'College program updated',
  college_program_verified: 'College program verified',
  college_catalog_imported: 'College catalog imported',
  program_family_saved: 'Program family saved',
  program_profile_applied: 'Program profile validated',
  interest_map_saved: 'Family interest map saved',
  interest_instrument_activated: 'Interest assessment activated',
  recommender_config_saved: 'Recommender settings saved',
  recommender_config_activated: 'Recommender settings activated',
  recommender_training_queued: 'Recommender training requested',
  recommender_training_finished: 'Recommender training finished',
  recommender_model_activated: 'Recommender model activated',
  recommender_model_archived: 'Recommender model switched off',
  recommender_permission_changed: 'Recommender permission changed',
  guidance_consent_given: 'Recommendation consent given',
  guidance_consent_withdrawn: 'Recommendation consent withdrawn',
  guidance_data_deleted: 'Recommendation answers deleted',
  guidance_student_viewed: 'Adviser opened college recommendation',
  adviser_note_added: 'Adviser note added',
  adviser_recommendation_added: 'Adviser recommendation added',
  college_outcome_recorded: 'College outcome recorded',
  college_outcome_validated: 'College outcome validated',
  logout: 'Signed out',
  login_locked: 'Sign-in paused after failed attempts',
  session_replay_detected: 'Stolen sign-in token blocked',
  sessions_ended_by_admin: 'Signed out on every device',
  register_duplicate: 'Registration repeated existing details',
  mfa_enrolled: 'Authenticator app set up',
  mfa_disabled: 'Authenticator app turned off',
  mfa_reset: 'Authenticator app reset',
  mfa_recovery_used: 'Recovery code used to sign in',
  mfa_recovery_codes_renewed: 'New recovery codes made',
  django_admin_login: 'Maintenance console sign-in',
  console_access_changed: 'Maintenance console access changed',
};

const ROLE_LABELS = {
  admin: 'Administrator',
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  student: 'Student',
};

const CATEGORY_LABELS = {
  accounts: 'Account',
  school: 'School',
  assignments: 'Assignment',
  placement: 'Placement',
  grades: 'Grades',
  announcements: 'Announcement',
  access: 'Access',
  guidance: 'College recommendation',
  security: 'Security',
};

export const AUDIT_FILTERS = EVENT_FAMILIES;

export function actionLabel(action) {
  return ACTION_LABELS[action] || String(action || '').replaceAll('_', ' ');
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || role || '—';
}

export function categoryLabel(category) {
  return CATEGORY_LABELS[category] || category || 'Notice';
}

function legacyActionFamily(action) {
  const code = String(action || '');
  if (code.startsWith('staff_')) return 'accounts';
  if (
    code.startsWith('account_') ||
    code === 'register' ||
    code === 'login' ||
    code === 'student_profile_updated' ||
    code === 'student_gender_set' ||
    code.startsWith('password_')
  ) {
    return 'accounts';
  }
  if (code.startsWith('program_') || code.startsWith('school_year_') || code.startsWith('section_') || code === 'deadline_set') {
    return 'school';
  }
  if (code.startsWith('assignment_') || code.endsWith('_assigned')) return 'assignments';
  if (code.startsWith('student_')) return 'placement';
  if (code.startsWith('cms_') || code.startsWith('announcement_')) return 'announcements';
  if (code.startsWith('access_')) return 'access';
  if (code.includes('grade') || code.includes('correction')) return 'grades';
  return 'accounts';
}

export function actionFamily(row) {
  if (row?.family) return row.family;
  return legacyActionFamily(row?.action);
}

export function familyIcon(family) {
  if (family === 'grades') return 'grades';
  if (family === 'school') return 'year';
  if (family === 'assignments') return 'assign';
  if (family === 'placement') return 'place';
  if (family === 'announcements') return 'cms';
  if (family === 'accounts') return 'user';
  if (family === 'access') return 'access';
  if (family === 'guidance') return 'guidance';
  if (family === 'security') return 'alert';
  return 'audit';
}

export function chipKind(family) {
  if (family === 'grades') return 'is-wait';
  if (family === 'announcements') return 'is-on';
  if (family === 'assignments' || family === 'school') return 'is-on';
  return 'is-wait';
}

function dayKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown date';
  return date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

export function timeLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || '—';
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

const DETAIL_LABELS = {
  note: 'Note',
  panel_approved: 'Panel approved',
  changes: 'Changed values',
  term: 'Term',
  term_label: 'Term',
  section: 'Section',
  subject: 'Subject',
  student: 'Student',
  from: 'From',
  to: 'To',
  reason: 'Reason',
  partial: 'Partial card',
  shown: 'Shown',
  hidden: 'Hidden',
  email: 'Email',
  still_shown: 'Still shown',
};

export function detailLines(details) {
  if (!details || typeof details !== 'object') return [];
  return Object.entries(details)
    .filter(([, value]) => value !== '' && value != null)
    .map(([key, value]) => ({
      label: DETAIL_LABELS[key] || key.replaceAll('_', ' '),
      value: typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value),
    }));
}

export function groupAuditRows(rows, family, query) {
  const needle = query.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    if (family !== 'all' && actionFamily(row) !== family) return false;
    if (!needle) return true;
    const hay = [actionLabel(row.action), row.actor, row.role, row.summary, JSON.stringify(row.details || {})]
      .join(' ')
      .toLowerCase();
    return hay.includes(needle);
  });

  const groups = [];
  const index = new Map();
  filtered.forEach((row) => {
    const key = dayKey(row.created_at);
    if (!index.has(key)) {
      const group = { day: key, rows: [] };
      index.set(key, group);
      groups.push(group);
    }
    index.get(key).rows.push(row);
  });
  return groups;
}

export function filterNotifications(rows, category, unreadOnly) {
  return rows.filter((row) => {
    if (unreadOnly && row.is_read) return false;
    if (category !== 'all' && row.category !== category) return false;
    return true;
  });
}
