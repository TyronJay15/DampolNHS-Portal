import { useState } from 'react';
import PasswordRules from '../../components/auth/PasswordRules';
import LineMark from '../../components/LineMark/LineMark';
import PageHead from '../../components/PageHead/PageHead';
import PasswordInput from '../../components/Input/PasswordInput';
import { useAuth } from '../../context/AuthContext';
import { changePassword, requestPasswordOtp } from '../../services/authService';
import { checkPassword, checkPasswordMatch, firstApiError } from '../../utils/authRules';
import './ChangePasswordPage.css';

const ROLE_LABEL = {
  student: 'Student',
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  admin: 'Admin',
};

export default function ChangePasswordPage() {
  const { user } = useAuth();
  const staff = user?.role && user.role !== 'student';
  const [currentPassword, setCurrentPassword] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSendCode() {
    setError('');
    setMessage('');
    if (!currentPassword) {
      setError('Enter your current password first.');
      return;
    }
    setSending(true);
    try {
      await requestPasswordOtp({ current_password: currentPassword });
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
      setMessage('Password updated.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="desk studio account-password">
      <PageHead kicker="My Account" title={staff ? 'Account' : 'Change password'} icon="account">
        <p>
          {staff
            ? 'Your profile and password sit side by side. Confirm the current password before you set a new one.'
            : 'Confirm the current password, collect the 6-digit code, then set the new one. Use at least 8 characters with a letter and a number.'}
        </p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className={staff ? 'account-desk' : 'account-password-desk'}>
        {staff ? (
          <section className="card studio-panel">
            <h2>
              <LineMark name="user" />
              Profile
            </h2>
            <dl className="account-facts">
              <div>
                <dt>Name</dt>
                <dd>
                  {user.first_name} {user.last_name}
                </dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{user.email}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{ROLE_LABEL[user.role] || user.role}</dd>
              </div>
            </dl>
          </section>
        ) : null}

        <form className={staff ? 'account-password-block' : undefined} onSubmit={handleSubmit}>
          <section className="card studio-panel">
            <h2>
              <LineMark name="account" />
              Verify you
            </h2>
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
            <button className="btn btn-secondary" type="button" onClick={handleSendCode} disabled={sending}>
              {sending ? 'Sending…' : 'Send email code'}
            </button>
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
          </section>

          <section className="card studio-panel">
            <h2>
              <LineMark name="account" />
              New password
            </h2>
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
              <PasswordRules value={newPassword} />
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
            <button className="btn" type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save password'}
            </button>
          </section>
        </form>
      </div>
    </div>
  );
}
