import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { beginPostLogin } from '../../components/PostLoginLoader/postLoginStore';
import RecaptchaField from '../../components/auth/RecaptchaField';
import PasswordInput from '../../components/Input/PasswordInput';
import { useAuth } from '../../context/AuthContext';
import AuthShell from './AuthShell';
import './LoginPage.css';

export default function LoginPage() {
  const { login } = useAuth();
  const location = useLocation();
  const notice = location.state?.notice || '';
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recaptchaToken, setRecaptchaToken] = useState('');
  const [recaptchaError, setRecaptchaError] = useState('');
  // Set only after a successful sign-in. The page stays mounted (blurred by the overlay) and inactive.
  const [entering, setEntering] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setPending(false);
    setRecaptchaError('');
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return;
    }
    setLoading(true);
    try {
      const result = await login({ identifier, password, recaptcha_token: recaptchaToken });
      setEntering(true);
      beginPostLogin(result.user.role);
    } catch (err) {
      const captcha = err.data?.errors?.recaptcha_token;
      const code = err.code || err.data?.code;
      setRecaptchaError(captcha ? [].concat(captcha).join(' ') : '');
      setError(captcha ? '' : err.message);
      setPending(code === 'account_pending');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Grading Portal" className="login-page">
      <form onSubmit={handleSubmit} inert={entering}>
        {notice ? <p className="alert alert-info">{notice}</p> : null}
        {error ? <p className={`alert ${pending ? 'alert-info' : 'alert-error'}`}>{error}</p> : null}
        {pending ? (
          <p>
            <Link className="auth-link" to="/registration-waiting">
              Check your application status
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
      <div className="auth-foot" inert={entering}>
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
