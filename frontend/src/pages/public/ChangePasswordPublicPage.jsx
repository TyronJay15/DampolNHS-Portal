import { useState } from 'react';
import { Link } from 'react-router-dom';
import PasswordRules from '../../components/auth/PasswordRules';
import PasswordInput from '../../components/Input/PasswordInput';
import { changePasswordPublic, requestPasswordOtpPublic } from '../../services/authService';
import { checkPassword, checkPasswordMatch, firstApiError } from '../../utils/authRules';
import AuthShell from './AuthShell';
import './LoginPage.css';

export default function ChangePasswordPublicPage() {
  const [identifier, setIdentifier] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldError, setFieldError] = useState('');
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSendCode(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    setSending(true);
    try {
      await requestPasswordOtpPublic({
        identifier,
        current_password: currentPassword,
      });
      setMessage('A 6-digit code was issued. Copy it from the Django terminal. It expires in 10 minutes.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSending(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    const passwordError = checkPassword(newPassword) || checkPasswordMatch(newPassword, confirmPassword);
    setFieldError(passwordError);
    if (passwordError) return;
    setSaving(true);
    try {
      await changePasswordPublic({
        identifier,
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
        code,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setCode('');
      setMessage('Password updated. You can sign in with the new password.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthShell title="Change password" className="login-page">
      <form onSubmit={handleSubmit}>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <label className="form-field">
          LRN or email
          <input
            type="text"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="form-field">
          Current password
          <PasswordInput
            name="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button className="btn btn-secondary" type="button" onClick={handleSendCode} disabled={sending || !identifier || !currentPassword}>
          {sending ? 'Sending…' : 'Send email code'}
        </button>
        <label className="form-field">
          Email code
          <input
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="6-digit code"
            required
          />
        </label>
        <label className="form-field">
          New password
          <PasswordInput
            name="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
          <PasswordRules value={newPassword} />
          {fieldError ? <span className="form-error">{fieldError}</span> : null}
        </label>
        <label className="form-field">
          Confirm new password
          <PasswordInput
            name="confirm-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <button className="btn" type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save password'}
        </button>
      </form>
      <div className="auth-foot">
        <p>
          Ready to sign in? <Link to="/login">Go to login</Link>
        </p>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
