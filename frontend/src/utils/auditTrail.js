export const EVENT_FAMILIES = [
  { value: 'all', label: 'All' },
  { value: 'accounts', label: 'Accounts' },
  { value: 'school', label: 'School' },
  { value: 'assignments', label: 'Assignments' },
  { value: 'placement', label: 'Placement' },
  { value: 'grades', label: 'Grades' },
  { value: 'announcements', label: 'Announcements' },
];

export const NOTIFICATION_FILTERS = EVENT_FAMILIES;

const ACTION_LABELS = {
  register: 'Registration submitted',
  login: 'Signed in',
  password_otp_requested: 'Password code sent',
  password_change: 'Password changed',
  account_approved: 'Student approved',
  account_rejected: 'Student rejected',
  account_archived: 'Account archived',
  account_reactivated: 'Account reactivated',
  account_removed: 'Account removed',
  registration_restored_pending: 'Registration reopened',
  student_profile_updated: 'Student profile updated',
  staff_created: 'Staff created',
  staff_activated: 'Staff activated',
  staff_activation_resent: 'Activation resent',
  school_year_created: 'School year opened',
  school_year_archived: 'School year archived',
  school_year_restored: 'School year restored',
  school_year_deleted: 'School year deleted',
  school_year_hard_deleted: 'School year hard deleted',
  deadline_set: 'Encode window set',
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
  ptpa_marked: 'PTPA marked',
  correction_requested: 'Correction requested',
  correction_approved: 'Correction approved',
  correction_rejected: 'Correction rejected',
  cms_save: 'Website saved',
  announcement_published: 'Event published',
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
  if (code.includes('grade') || code.includes('correction') || code.includes('ptpa')) return 'grades';
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
