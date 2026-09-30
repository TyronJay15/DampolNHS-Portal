export function programChangeNote(student, section) {
  if (!student?.program_code || !section?.program_code || student.program_code === section.program_code) return '';
  return `This also moves ${student.name} from ${student.program_code} to ${section.program_code}.`;
}

export function isCapacityError(err) {
  return /capacity/i.test(err?.message || '');
}
