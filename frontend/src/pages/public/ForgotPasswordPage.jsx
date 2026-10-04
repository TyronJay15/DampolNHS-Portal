import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import PasswordRules from '../../components/auth/PasswordRules';
import RecaptchaField from '../../components/auth/RecaptchaField';
import ResendCodeButton from '../../components/auth/ResendCodeButton';
import { nextResendAt } from '../../components/auth/resendTime';
import StepTrail from '../../components/auth/StepTrail';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import PasswordInput from '../../components/Input/PasswordInput';
import {
  requestForgotPasswordOtp,
  resetForgottenPassword,
  verifyForgotPasswordOtp,
} from '../../services/authService';
import { checkPassword, checkPasswordMatch, firstApiError } from '../../utils/authRules';
import AuthShell from './AuthShell';
import './LoginPage.css';

// Same three steps as Change password: find the account and email a code, verify it, set the new password.
const STEPS = [
  { id: 'send', label: 'Your account' },
  { id: 'verify', label: 'Verify code' },
  { id: 'password', label: 'New password' },
];

function captchaMessage(err) {
  const captcha = err.data?.errors?.recaptcha_token;
  return captcha ? [].concat(captcha).join(' ') : '';
}

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const [step, setStep] = useState('send');
  const [identifier, setIdentifier] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [recaptchaToken, setRecaptchaToken] = useState('');
  const [recaptchaError, setRecaptchaError] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [resendAt, setResendAt] = useState(0);

  function startRequest() {
    setError('');
    setMessage('');
    setRecaptchaError('');
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return false;
    }
    return true;
  }

  function showError(err) {
    const captcha = captchaMessage(err);
    setRecaptchaError(captcha);
    setError(captcha ? '' : firstApiError(err));
  }

  async function handleSendCode() {
    if (!startRequest()) return;
    setBusy('send');
    try {
      const data = await requestForgotPasswordOtp({ identifier, recaptcha_token: recaptchaToken });
      setResendAt(nextResendAt(data));
      setStep('verify');
      setMessage('If that account exists, a 6-digit code was sent to its email. It expires in 10 minutes.');
    } catch (err) {
      showError(err);
    } finally {
      setBusy('');
    }
  }

  async function handleVerifyCode(event) {
    event.preventDefault();
    if (!startRequest()) return;
    if (code.length !== 6) {
      setError('Enter the 6-digit code from your email.');
      return;
    }
    setBusy('verify');
    try {
      await verifyForgotPasswordOtp({ identifier, code, recaptcha_token: recaptchaToken });
      setStep('password');
      setMessage('Code verified. Set a new password.');
    } catch (err) {
      showError(err);
    } finally {
      setBusy('');
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!startRequest()) return;
    const passwordError = checkPassword(newPassword) || checkPasswordMatch(newPassword, confirmPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    setBusy('save');
    try {
      await resetForgottenPassword({
        identifier,
        code,
        new_password: newPassword,
        confirm_password: confirmPassword,
        recaptcha_token: recaptchaToken,
      });
    } catch (err) {
      showError(err);
      setBusy('');
      return;
    }
    await confirm({
      title: 'Password reset',
      body: 'Your password has been reset. Sign in with your new password to continue.',
      confirmLabel: 'Go to sign in',
      cancelLabel: null,
    });
    navigate('/login', { replace: true });
  }

  function chooseAnotherAccount() {
    setStep('send');
    setCode('');
    setMessage('');
    setError('');
  }

  return (
    <AuthShell title="Forgot password" className="login-page">
      <StepTrail steps={STEPS} current={step} className="auth-steps" />
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      {step === 'send' ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            handleSendCode();
          }}
        >
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
          <button className="btn" type="submit" disabled={Boolean(busy) || !identifier}>
            {busy === 'send' ? 'Sending…' : 'Send reset code'}
          </button>
        </form>
      ) : null}

      {step === 'verify' ? (
        <form onSubmit={handleVerifyCode}>
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
          <RecaptchaField onChange={setRecaptchaToken} error={recaptchaError} />
          <button className="btn" type="submit" disabled={Boolean(busy)}>
            {busy === 'verify' ? 'Verifying…' : 'Verify code'}
          </button>
          <ResendCodeButton availableAt={resendAt} onResend={handleSendCode} busy={busy === 'send'} />
          <button className="auth-link-button" type="button" onClick={chooseAnotherAccount}>
            Use a different account
          </button>
        </form>
      ) : null}

      {step === 'password' ? (
        <form onSubmit={handleSubmit}>
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
          <RecaptchaField onChange={setRecaptchaToken} error={recaptchaError} />
          <button className="btn" type="submit" disabled={Boolean(busy)}>
            {busy === 'save' ? 'Saving…' : 'Save new password'}
          </button>
        </form>
      ) : null}

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
