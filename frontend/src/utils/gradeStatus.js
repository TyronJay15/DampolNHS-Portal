export function gradeStatusIcon(status) {
  if (status === 'submitted') return 'history';
  if (status === 'approved') return 'approve';
  if (status === 'released') return 'check';
  if (status === 'draft') return 'pencil';
  return 'grades';
}

export function cardStatusIcon(row) {
  if (row?.update_ready) return 'approve';
  if (row?.shown) return 'check';
  if (row?.ready) return 'approve';
  if (row?.partial) return 'history';
  return 'history';
}

export function cardStatusLabel(row) {
  if (row?.update_ready) return `Update ready ${row.posted}/${row.assigned}`;
  if (row?.shown) return 'Shown';
  if (row?.partial) return `Shown ${row.released || row.posted}/${row.assigned}`;
  if (row?.ready && !row?.complete) return `Ready ${row.posted}/${row.assigned}`;
  if (row?.ready) return 'Ready to show';
  if (row?.assigned) return `Waiting ${row.posted || 0}/${row.assigned}`;
  return 'Waiting for approval';
}

export function cardStatusClass(row) {
  if (row?.update_ready) return 'is-ready';
  if (row?.shown) return 'is-shown';
  if (row?.partial || row?.ready) return 'is-ready';
  return '';
}

export function progressChipClass(progress) {
  if (progress === 'encoded') return 'is-encoded';
  if (progress === 'in_progress') return 'is-progress';
  return 'is-wait';
}
