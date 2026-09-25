import { useState } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import './RecaptchaField.css';

const SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || '';

export default function RecaptchaField({ onChange, error }) {
  const [demo, setDemo] = useState(false);

  if (!SITE_KEY) {
    return (
      <div className="recaptcha-field">
        <label className="recaptcha-demo">
          <input
            type="checkbox"
            checked={demo}
            onChange={(event) => {
              setDemo(event.target.checked);
              onChange(event.target.checked ? 'demo' : '');
            }}
          />
          I am not a robot
        </label>
        {error ? <p className="recaptcha-error">{error}</p> : null}
      </div>
    );
  }

  return (
    <div className="recaptcha-field">
      <p className="recaptcha-label">Security verification</p>
      <div className="recaptcha-widget">
        <ReCAPTCHA
          sitekey={SITE_KEY}
          onChange={(token) => onChange(token || '')}
          onExpired={() => onChange('')}
        />
      </div>
      {error ? <p className="recaptcha-error">{error}</p> : null}
    </div>
  );
}
