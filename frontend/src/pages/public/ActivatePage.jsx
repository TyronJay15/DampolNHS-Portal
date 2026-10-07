import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import PasswordRules from '../../components/auth/PasswordRules';
import PasswordInput from '../../components/Input/PasswordInput';
import { activateAccount } from '../../services/authService';
import { STAFF_PASSWORD_MIN, checkPassword, checkPasswordMatch, firstApiError } from '../../utils/authRules';
import AuthShell from './AuthShell';
import './LoginPage.css';

export default function ActivatePage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    const passwordError = checkPassword(password, STAFF_PASSWORD_MIN) || checkPasswordMatch(password, confirmPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    setSaving(true);
    try {
      await activateAccount({
        email,
        code,
        password,
        confirm_password: confirmPassword,
      });
      setMessage('Account ready. Check your email, then sign in with the password you set.');
      setTimeout(() => navigate('/login'), 1600);
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthShell title="Activate account" className="login-page">
      <form onSubmit={handleSubmit}>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <label className="form-field">
          School email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label className="form-field">
          Activation code
          <input
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="6-digit code"
            required
          />
          <span className="auth-hint">Use the code from your activation email.</span>
        </label>
        <label className="form-field">
          New password
          <PasswordInput
            name="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
          <PasswordRules value={password} min={STAFF_PASSWORD_MIN} />
        </label>
        <label className="form-field">
          Confirm password
          <PasswordInput
            name="confirm-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <button className="btn" type="submit" disabled={saving}>
          {saving ? 'Activating…' : 'Activate account'}
        </button>
      </form>
      <div className="auth-foot">
        <p>
          Already activated? <Link to="/login">Sign in</Link>
        </p>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
