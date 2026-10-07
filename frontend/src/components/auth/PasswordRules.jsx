import { STUDENT_PASSWORD_MIN, passwordChecks } from '../../utils/authRules';
import './PasswordRules.css';

export default function PasswordRules({ value, min = STUDENT_PASSWORD_MIN }) {
  const checks = passwordChecks(value, min);
  const rules = [
    ['length', `At least ${min} characters`],
    ['letter', 'At least one letter'],
    ['number', 'At least one number'],
  ];
  return (
    <ul className="password-rules">
      {rules.map(([key, label]) => (
        <li key={key} className={checks[key] ? 'is-ok' : ''}>
          {label}
        </li>
      ))}
    </ul>
  );
}
