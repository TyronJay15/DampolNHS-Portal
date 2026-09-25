import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import RecaptchaField from '../../components/auth/RecaptchaField';
import PasswordRules from '../../components/auth/PasswordRules';
import PasswordInput from '../../components/Input/PasswordInput';
import { requestForgotPasswordOtp, resetForgottenPassword } from '../../services/authService';
import { checkPassword, checkPasswordMatch, firstApiError } from '../../utils/authRules';
import AuthShell from './AuthShell';
import './LoginPage.css';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [recaptchaToken, setRecaptchaToken] = useState('');
  const [recaptchaError, setRecaptchaError] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSendCode() {
    setError('');
    setMessage('');
    setRecaptchaError('');
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return;
    }
    setSending(true);
    try {
      const data = await requestForgotPasswordOtp({ identifier, recaptcha_token: recaptchaToken });
      setMessage(data.detail || 'If that account exists, a code was sent.');
    } catch (err) {
      const captcha = err.data?.errors?.recaptcha_token;
      setRecaptchaError(captcha ? [].concat(captcha).join(' ') : '');
      setError(captcha ? '' : firstApiError(err));
    } finally {
      setSending(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    setRecaptchaError('');
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return;
    }
    const passwordError = checkPassword(newPassword) || checkPasswordMatch(newPassword, confirmPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    setSaving(true);
    try {
      await resetForgottenPassword({
        identifier,
        code,
        new_password: newPassword,
        confirm_password: confirmPassword,
        recaptcha_token: recaptchaToken,
      });
      navigate('/login', { replace: true, state: { notice: 'Password updated. Sign in with the new password.' } });
    } catch (err) {
      const captcha = err.data?.errors?.recaptcha_token;
      setRecaptchaError(captcha ? [].concat(captcha).join(' ') : '');
      setError(captcha ? '' : firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthShell title="Forgot password" className="login-page">
      <form onSubmit={handleSubmit}>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <label className="form-field">
          LRN or email
          <input
            type="text"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder="2025-000000001 or name@dampol1nhs.edu.ph"
            autoComplete="username"
            required
          />
        </label>
        <RecaptchaField onChange={setRecaptchaToken} error={recaptchaError} />
        <button className="btn btn-secondary" type="button" onClick={handleSendCode} disabled={sending || !identifier}>
          {sending ? 'Sending…' : 'Send reset code'}
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
          {saving ? 'Saving…' : 'Save new password'}
        </button>
      </form>
      <div className="auth-foot">
        <p>
          Remembered it? <Link to="/login">Back to sign in</Link>
        </p>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
