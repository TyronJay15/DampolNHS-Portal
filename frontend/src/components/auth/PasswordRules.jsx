import { passwordChecks } from '../../utils/authRules';
import './PasswordRules.css';

const RULES = [
  ['length', 'At least 8 characters'],
  ['letter', 'At least one letter'],
  ['number', 'At least one number'],
];

export default function PasswordRules({ value }) {
  const checks = passwordChecks(value);
  return (
    <ul className="password-rules">
      {RULES.map(([key, label]) => (
        <li key={key} className={checks[key] ? 'is-ok' : ''}>
          {label}
        </li>
      ))}
    </ul>
  );
}
