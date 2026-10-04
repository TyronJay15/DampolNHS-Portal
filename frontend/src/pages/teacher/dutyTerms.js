// A duty only shows the terms the Head Teacher scheduled for it (plus any term that already holds grades).
// The server sends those term ids on each duty as `terms`.
export function dutyTerms(termRows, assignment) {
  const offered = new Set(assignment?.terms || []);
  return termRows.filter((row) => offered.has(row.id));
}

export function defaultTermId(termRows) {
  const current = termRows.find((row) => row.is_current) || termRows[0];
  return current ? String(current.id) : '';
}

// Short line for a duty card: the current term when the subject runs in it, else the terms it runs in.
export function dutyTermNote(row) {
  const progress = row.progress;
  if (progress?.current?.term) return progress.current.term;
  if (progress?.terms?.length) return `Runs in ${progress.terms.map((term) => term.term).join(', ')}`;
  return 'No term scheduled';
}
