import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import RecaptchaField from '../../components/auth/RecaptchaField';
import PasswordInput from '../../components/Input/PasswordInput';
import { useAuth } from '../../context/AuthContext';
import { homePathForRole } from '../../services/authService';
import AuthShell from './AuthShell';
import './LoginPage.css';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const notice = location.state?.notice || '';
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [needsActivation, setNeedsActivation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recaptchaToken, setRecaptchaToken] = useState('');
  const [recaptchaError, setRecaptchaError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setPending(false);
    setNeedsActivation(false);
    setRecaptchaError('');
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return;
    }
    setLoading(true);
    try {
      const user = await login({ identifier, password, recaptcha_token: recaptchaToken });
      navigate(homePathForRole(user.role));
    } catch (err) {
      const captcha = err.data?.errors?.recaptcha_token;
      const code = err.code || err.data?.code;
      setRecaptchaError(captcha ? [].concat(captcha).join(' ') : '');
      setError(captcha ? '' : err.message);
      setPending(code === 'account_pending');
      setNeedsActivation(code === 'account_needs_activation');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Grading Portal" className="login-page">
      <form onSubmit={handleSubmit}>
        {notice ? <p className="alert alert-info">{notice}</p> : null}
        {error ? <p className={`alert ${pending || needsActivation ? 'alert-info' : 'alert-error'}`}>{error}</p> : null}
        {pending ? (
          <p>
            <Link className="auth-link" to="/registration-waiting">
              Check your application status
            </Link>
          </p>
        ) : null}
        {needsActivation ? (
          <p>
            <Link className="auth-link" to="/activate">
              Activate your account
            </Link>
          </p>
        ) : null}
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
          <span className="auth-hint">Students use LRN. Staff use school email.</span>
        </label>
        <label className="form-field">
          Password
          <PasswordInput
            name="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          <span className="auth-hint">
            <Link className="auth-link" to="/forgot-password">
              Forgot password?
            </Link>
          </span>
        </label>
        <RecaptchaField onChange={setRecaptchaToken} error={recaptchaError} />
        <button className="btn" type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <div className="auth-foot">
        <p>
          New staff member? <Link to="/activate">Activate account</Link>
        </p>
        <p>
          Don&apos;t have an account? <Link to="/register">Sign up</Link>
        </p>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
