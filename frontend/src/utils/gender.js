// Matches StudentProfile.Gender on the server.
export const GENDER_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

export function genderLabel(value) {
  return GENDER_OPTIONS.find((option) => option.value === value)?.label || '—';
}
