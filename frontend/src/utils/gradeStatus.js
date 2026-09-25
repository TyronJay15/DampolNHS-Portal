export function gradeStatusIcon(status) {
  if (status === 'submitted') return 'history';
  if (status === 'approved') return 'approve';
  if (status === 'released') return 'check';
  if (status === 'draft') return 'pencil';
  return 'grades';
}

export function cardStatusIcon(row) {
  if (row?.shown) return 'check';
  if (row?.ready) return 'approve';
  return 'history';
}
