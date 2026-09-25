import { useState } from 'react';
import './PasswordInput.css';

export default function PasswordInput({ id, name, value, onChange, autoComplete, required }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-wrap">
      <input
        id={id}
        name={name}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        required={required}
      />
      <button
        type="button"
        className="password-toggle"
        aria-label={visible ? 'Hide password' : 'Show password'}
        onClick={() => setVisible((open) => !open)}
      >
        {visible ? (
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 6c5 0 9 4.5 10 6-1 1.5-5 6-10 6S3 13.5 2 12c1-1.5 5-6 10-6zm0 3.5A2.5 2.5 0 1 0 12 14a2.5 2.5 0 0 0 0-4.5zM4.7 4.7l14.6 14.6-1.4 1.4L3.3 6.1z"
            />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 6c5 0 9 4.5 10 6-1 1.5-5 6-10 6S3 13.5 2 12c1-1.5 5-6 10-6zm0 3.5A2.5 2.5 0 1 0 12 14a2.5 2.5 0 0 0 0-4.5z"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
