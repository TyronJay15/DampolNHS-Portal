import { useState } from 'react';
import AuthenticatorSettings from '../../components/auth/AuthenticatorSettings';
import PasswordRules from '../../components/auth/PasswordRules';
import ResendCodeButton from '../../components/auth/ResendCodeButton';
import { nextResendAt } from '../../components/auth/resendTime';
import StepTrail from '../../components/auth/StepTrail';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import MoreMenu from '../../components/MoreMenu/MoreMenu';
import PageHead from '../../components/PageHead/PageHead';
import PasswordInput from '../../components/Input/PasswordInput';
import { useAuth } from '../../context/AuthContext';
import { changePassword, requestPasswordOtp, verifyPasswordOtp } from '../../services/authService';
import { checkPassword, checkPasswordMatch, firstApiError, passwordMinFor } from '../../utils/authRules';
import '../../styles/studio.css';
import './ChangePasswordPage.css';

// Printable exports, reached from the quiet "⋯" menu. The server decides what each role may see.
const PRINT_ITEMS = {
  student: [{ to: '/print/grades', label: 'Print grades' }],
  teacher: [{ to: '/print/records', label: 'Print my grade records' }],
  head_teacher: [{ to: '/print/records', label: 'Print my grade records' }],
};

const STEPS = [
  { id: 'send', label: 'Current password' },
  { id: 'verify', label: 'Verify code' },
  { id: 'password', label: 'New password' },
];

const ROLE_LABEL = {
  student: 'Student',
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  admin: 'Admission',
};

export default function ChangePasswordPage() {
  const { user } = useAuth();
  const minimum = passwordMinFor(user?.role);
  const confirm = useConfirm();
  const [step, setStep] = useState('send');
  const [currentPassword, setCurrentPassword] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resendAt, setResendAt] = useState(0);

  async function handleSendCode() {
    setError('');
    setMessage('');
    if (!currentPassword) {
      setError('Enter your current password first.');
      return;
    }
    setSending(true);
    try {
      const data = await requestPasswordOtp({ current_password: currentPassword });
      setResendAt(nextResendAt(data));
      setStep('verify');
      setMessage('A 6-digit code was sent to your email. It expires in 10 minutes.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSending(false);
    }
  }

  async function handleVerifyCode(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    if (code.length !== 6) {
      setError('Enter the 6-digit code from your email.');
      return;
    }
    setVerifying(true);
    try {
      await verifyPasswordOtp({ current_password: currentPassword, code });
      setStep('password');
      setMessage('Code verified. Set a new password.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setVerifying(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    const passwordError = checkPassword(newPassword, minimum) || checkPasswordMatch(newPassword, confirmPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    setSaving(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
        code,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setCode('');
      setStep('send');
      await confirm({
        title: 'Password changed',
        body: 'Your new password is saved. Use it the next time you sign in on any device.',
        confirmLabel: 'Done',
        cancelLabel: null,
      });
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="desk studio account-page">
      <PageHead kicker="My Account" title="Account" icon="account">
        <p>Confirm your current password, verify the email code, then set a new password.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{ROLE_LABEL[user?.role] || user?.role || 'Account'}</span>
          {user?.email ? <span className="studio-chip">{user.email}</span> : null}
        </div>
      </PageHead>
      <MoreMenu items={PRINT_ITEMS[user?.role] || []} />
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="account-desk">
        <section className="card studio-panel">
          <h2>
            <LineMark name="user" />
            Profile
          </h2>
          <dl className="account-facts">
            <div>
              <dt>Name</dt>
              <dd>
                {user?.first_name} {user?.last_name}
              </dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user?.email || '—'}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{ROLE_LABEL[user?.role] || user?.role || '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="card studio-panel">
          <h2>
            <LineMark name="account" />
            Password
          </h2>
          <StepTrail steps={STEPS} current={step} className="account-steps" />

          {step === 'send' ? (
            <form
              className="account-password-form is-step"
              onSubmit={(event) => {
                event.preventDefault();
                handleSendCode();
              }}
            >
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="account" size={14} />
                  Current password
                </span>
                <PasswordInput
                  name="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>
              <div className="account-password-foot">
                <button className="btn" type="submit" disabled={sending}>
                  {sending ? 'Sending…' : 'Send email code'}
                </button>
              </div>
            </form>
          ) : null}

          {step === 'verify' ? (
            <form className="account-password-form is-step" onSubmit={handleVerifyCode}>
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="mail" size={14} />
                  Email code
                </span>
                <input
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="6-digit code"
                  required
                />
              </label>
              <div className="account-password-foot">
                <ResendCodeButton availableAt={resendAt} onResend={handleSendCode} busy={sending} />
                <button className="btn" type="submit" disabled={verifying}>
                  {verifying ? 'Verifying…' : 'Verify code'}
                </button>
              </div>
            </form>
          ) : null}

          {step === 'password' ? (
            <form className="account-password-form is-step" onSubmit={handleSubmit}>
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="account" size={14} />
                  New password
                </span>
                <PasswordInput
                  name="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  autoComplete="new-password"
                  required
                />
                <PasswordRules value={newPassword} min={minimum} />
              </label>
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="check" size={14} />
                  Confirm new password
                </span>
                <PasswordInput
                  name="confirm-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                  required
                />
              </label>
              <div className="account-password-foot">
                <button className="btn" type="submit" disabled={saving}>
                  {saving ? 'Saving…' : 'Save password'}
                </button>
              </div>
            </form>
          ) : null}
        </section>
      </div>
      {user?.role === 'admin' || user?.role === 'head_teacher' ? <AuthenticatorSettings /> : null}
    </div>
  );
}
