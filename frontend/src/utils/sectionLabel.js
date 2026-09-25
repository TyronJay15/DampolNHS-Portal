export function sectionLabel(row) {
  if (!row) return '';
  if (row.display_label) return row.display_label;
  if (row.section && String(row.section).includes(' - ')) return row.section;
  const grade = String(row.grade_level || '').includes('12') ? '12' : String(row.grade_level || '').includes('11') ? '11' : '';
  const program = row.program_code || row.program || '';
  const name = row.name || row.section_name || row.section || '';
  const head = [grade, program].filter(Boolean).join(' - ');
  return head && name ? `${head} ${name}` : head || name;
}
