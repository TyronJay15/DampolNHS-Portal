const ACTION_LABELS = {
  account_approved: 'Student approved',
  account_rejected: 'Student rejected',
  account_deactivated: 'Account deactivated',
  account_reactivated: 'Account reactivated',
  school_year_created: 'School year opened',
  school_year_archived: 'School year archived',
  school_year_restored: 'School year restored',
  school_year_deleted: 'School year deleted',
  section_archived: 'Section archived',
  section_restored: 'Section restored',
  register: 'Registration submitted',
  login: 'Signed in',
  password_otp_requested: 'Password code sent',
  password_change: 'Password changed',
  staff_created: 'Staff created',
  staff_activated: 'Staff activated',
  staff_activation_resent: 'Activation resent',
  cms_save: 'Website saved',
  deadline_set: 'Encode window set',
  grade_encoded: 'Grade encoded',
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
};

const ROLE_LABELS = {
  admin: 'Administrator',
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  student: 'Student',
};

export const AUDIT_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'accounts', label: 'Accounts' },
  { value: 'staff', label: 'Staff' },
  { value: 'grades', label: 'Grades' },
  { value: 'website', label: 'Website' },
];

export function actionLabel(action) {
  return ACTION_LABELS[action] || String(action || '').replaceAll('_', ' ');
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || role || '—';
}

export function actionFamily(action) {
  const code = String(action || '');
  if (code.startsWith('staff_')) return 'staff';
  if (
    code.startsWith('account_') ||
    code === 'register' ||
    code === 'login' ||
    code === 'student_profile_updated' ||
    code === 'school_year_created' ||
    code.startsWith('password_')
  ) {
    return 'accounts';
  }
  if (code.startsWith('cms_')) return 'website';
  if (
    code.includes('grade') ||
    code.includes('correction') ||
    code.includes('deadline') ||
    code.includes('ptpa')
  ) {
    return 'grades';
  }
  return 'other';
}

export function familyIcon(family) {
  if (family === 'staff') return 'staff';
  if (family === 'grades') return 'grades';
  if (family === 'website') return 'cms';
  if (family === 'accounts') return 'user';
  return 'audit';
}

export function chipKind(family) {
  if (family === 'grades') return 'is-wait';
  if (family === 'website') return 'is-on';
  if (family === 'staff') return 'is-on';
  return 'is-wait';
}

export function dayKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown date';
  return date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

export function timeLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || '—';
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

export function groupAuditRows(rows, family, query) {
  const needle = query.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    if (family !== 'all' && actionFamily(row.action) !== family) return false;
    if (!needle) return true;
    const hay = [actionLabel(row.action), row.actor, row.role, row.summary].join(' ').toLowerCase();
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
