import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import PasswordRules from '../../components/auth/PasswordRules';
import PrivacyNotice from '../../components/auth/PrivacyNotice';
import RecaptchaField from '../../components/auth/RecaptchaField';
import PasswordInput from '../../components/Input/PasswordInput';
import { registerStudent } from '../../services/authService';
import { fetchPrograms } from '../../services/publicService';
import {
  checkAddress,
  checkContact,
  checkLrn,
  checkPassword,
  checkPasswordMatch,
  flattenErrors,
} from '../../utils/authRules';
import AuthShell from './AuthShell';
import './RegisterPage.css';

const emptyForm = {
  last_name: '',
  middle_name: '',
  first_name: '',
  lrn: '',
  email: '',
  contact_number: '',
  address: '',
  grade_level_enrollment: '',
  program: '',
  password: '',
  confirm_password: '',
};

function FieldError({ errors, name }) {
  if (!errors[name]) return null;
  return <span className="form-error">{errors[name]}</span>;
}

export default function RegisterPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [programs, setPrograms] = useState([]);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recaptchaToken, setRecaptchaToken] = useState('');
  const [recaptchaError, setRecaptchaError] = useState('');

  useEffect(() => {
    const selected = (params.get('program') || '').toUpperCase();
    fetchPrograms()
      .then((data) => {
        const items = Array.isArray(data) ? data : data.results || [];
        setPrograms(items);
        const match = items.find((item) => item.code === selected);
        setForm((prev) => ({
          ...prev,
          program: match ? match.code : prev.program,
          grade_level_enrollment: match?.grade_level || prev.grade_level_enrollment,
        }));
      })
      .catch(() => {});
  }, [params]);

  function update(event) {
    const { name, value } = event.target;
    if (name === 'lrn' && value && /[^0-9-]/.test(value)) return;
    if (name === 'contact_number' && value && /[^0-9]/.test(value)) return;
    if (name === 'program') {
      const chosen = programs.find((item) => item.code === value);
      setForm((prev) => ({
        ...prev,
        program: value,
        grade_level_enrollment: chosen?.grade_level || prev.grade_level_enrollment,
      }));
      return;
    }
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function localErrors() {
    return {
      lrn: checkLrn(form.lrn),
      contact_number: checkContact(form.contact_number),
      address: checkAddress(form.address),
      password: checkPassword(form.password),
      confirm_password: checkPasswordMatch(form.password, form.confirm_password),
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setRecaptchaError('');
    const nextErrors = localErrors();
    setFieldErrors(nextErrors);
    if (Object.values(nextErrors).some(Boolean)) return;
    if (!consent) {
      setError('Please accept the Data Privacy notice to continue.');
      return;
    }
    if (!recaptchaToken) {
      setRecaptchaError('Please complete the reCAPTCHA.');
      return;
    }
    setLoading(true);
    try {
      await registerStudent({ ...form, recaptcha_token: recaptchaToken });
      navigate('/registration-waiting');
    } catch (err) {
      const captcha = err.data?.errors?.recaptcha_token;
      setRecaptchaError(captcha ? [].concat(captcha).join(' ') : '');
      setError(captcha ? '' : err.message);
      setFieldErrors(flattenErrors(err.data?.errors));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Admission Registration" wide className="register-page">
      <form onSubmit={handleSubmit}>
        {error ? <p className="alert alert-error">{error}</p> : null}
        {form.program ? <p className="auth-hint">Selected program: {form.program}</p> : null}
        <div className="register-grid-3">
          <label className="form-field">
            Last name
            <input name="last_name" value={form.last_name} onChange={update} required />
          </label>
          <label className="form-field">
            Middle name
            <input name="middle_name" value={form.middle_name} onChange={update} />
          </label>
          <label className="form-field">
            First name
            <input name="first_name" value={form.first_name} onChange={update} required />
          </label>
        </div>
        <div className="register-grid-2">
          <label className="form-field">
            LRN
            <input name="lrn" value={form.lrn} onChange={update} maxLength={20} required />
            <FieldError errors={fieldErrors} name="lrn" />
          </label>
          <label className="form-field">
            Email
            <input type="email" name="email" value={form.email} onChange={update} required />
            <FieldError errors={fieldErrors} name="email" />
          </label>
        </div>
        <div className="register-grid-2">
          <label className="form-field">
            Contact number
            <input name="contact_number" inputMode="numeric" value={form.contact_number} onChange={update} maxLength={11} required />
            <FieldError errors={fieldErrors} name="contact_number" />
          </label>
          <label className="form-field">
            Grade level
            <input value={form.grade_level_enrollment} readOnly />
            <span className="auth-hint">
              {form.grade_level_enrollment
                ? `Locked to ${form.grade_level_enrollment} for this program.`
                : 'Grade locks when you choose a Grade 12 strand or Grade 11 cluster.'}
            </span>
          </label>
        </div>
        <label className="form-field">
          Program
          <select name="program" value={form.program} onChange={update} required>
            <option value="">Select program</option>
            <optgroup label="Grade 12 Strands">
              {programs
                .filter((item) => item.grade_level === 'Grade 12')
                .map((program) => (
                  <option key={program.code} value={program.code}>
                    {program.code} — {program.name}
                  </option>
                ))}
            </optgroup>
            <optgroup label="Grade 11 Cluster Programs">
              {programs
                .filter((item) => item.grade_level === 'Grade 11')
                .map((program) => (
                  <option key={program.code} value={program.code}>
                    {program.code} — {program.name}
                  </option>
                ))}
            </optgroup>
          </select>
        </label>
        <label className="form-field">
          Address
          <textarea name="address" rows={3} value={form.address} onChange={update} maxLength={255} required />
          <FieldError errors={fieldErrors} name="address" />
        </label>
        <div className="register-grid-2">
          <label className="form-field">
            Password
            <PasswordInput name="password" value={form.password} onChange={update} required />
            <PasswordRules value={form.password} />
            <FieldError errors={fieldErrors} name="password" />
          </label>
          <label className="form-field">
            Confirm password
            <PasswordInput name="confirm_password" value={form.confirm_password} onChange={update} required />
            <FieldError errors={fieldErrors} name="confirm_password" />
          </label>
        </div>
        <PrivacyNotice />
        <label className="register-consent">
          <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
          I have read and agree to the Data Privacy Act of 2012 consent statement.
        </label>
        <RecaptchaField onChange={setRecaptchaToken} error={recaptchaError} />
        <button className="btn" type="submit" disabled={loading}>
          {loading ? 'Submitting…' : 'Submit registration'}
        </button>
      </form>
      <div className="auth-foot">
        <p>
          Already registered? <Link to="/login">Sign in</Link>
        </p>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
