export function firstApiError(err) {
  const errors = err.data?.errors;
  if (errors && typeof errors === 'object') {
    for (const value of Object.values(errors)) {
      const text = Array.isArray(value) ? value[0] : value;
      if (text) return String(text);
    }
  }
  return err.message;
}

export function flattenErrors(errors) {
  const out = {};
  Object.entries(errors || {}).forEach(([key, value]) => {
    out[key] = Array.isArray(value) ? value.join(' ') : String(value);
  });
  return out;
}

export function lrnDigits(value) {
  return String(value || '').replace(/\D/g, '');
}

export function checkLrn(value) {
  const text = String(value || '').trim();
  if (/[^0-9-]/.test(text)) return 'LRN may contain numbers and hyphens only.';
  if (lrnDigits(text).length !== 12) return 'LRN must be 12 digits.';
  return '';
}

export function checkContact(value) {
  const digits = String(value || '').replace(/\D/g, '');
  if (!/^09\d{9}$/.test(digits)) return 'Contact number must be 11 digits starting with 09.';
  return '';
}

export function checkAddress(value) {
  const text = String(value || '').trim();
  if (text.length < 10 || text.length > 255) return 'Address must be 10 to 255 characters.';
  return '';
}

export function passwordChecks(value) {
  const text = String(value || '');
  return {
    length: text.length >= 8,
    letter: /[A-Za-z]/.test(text),
    number: /\d/.test(text),
  };
}

export function checkPassword(value) {
  const checks = passwordChecks(value);
  if (!checks.length) return 'Use at least 8 characters.';
  if (!checks.letter) return 'Include at least one letter.';
  if (!checks.number) return 'Include at least one number.';
  return '';
}

export function checkPasswordMatch(password, confirm) {
  if (password && confirm && password !== confirm) return 'Passwords do not match.';
  return '';
}
