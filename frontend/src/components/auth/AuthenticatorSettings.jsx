import { useEffect, useState } from 'react';
import LineMark from '../LineMark/LineMark';
import PasswordInput from '../Input/PasswordInput';
import {
  confirmMfaSetup,
  fetchMfaStatus,
  renewRecoveryCodes,
  startMfaSetup,
  turnOffMfa,
} from '../../services/authService';
import { firstApiError } from '../../utils/authRules';
import RecoveryCodes from './RecoveryCodes';
import './MfaStep.css';

/** Account page: the authenticator app of an Admin or Head Teacher. Every change needs the password, and a
 * current code once the app is set up. */
export default function AuthenticatorSettings() {
  const [status, setStatus] = useState(null);
  const [mode, setMode] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [setup, setSetup] = useState(null);
  const [codes, setCodes] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function load() {
    return fetchMfaStatus()
      .then(setStatus)
      .catch((err) => setError(firstApiError(err)));
  }

  useEffect(() => {
    load();
  }, []);

  function reset(nextMode = '') {
    setMode(nextMode);
    setPassword('');
    setCode('');
    setSetup(null);
    setError('');
  }

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (err) {
      setError(firstApiError(err));
      setCode('');
    } finally {
      setBusy(false);
    }
  }

  const start = (event) => {
    event.preventDefault();
    run(async () => setSetup(await startMfaSetup(password)));
  };
  const finish = (event) => {
    event.preventDefault();
    run(async () => {
      const result = await confirmMfaSetup(code.trim());
      reset();
      setCodes(result.recovery_codes);
      await load();
    });
  };
  const renew = (event) => {
    event.preventDefault();
    run(async () => {
      const result = await renewRecoveryCodes({ password, code: code.trim() });
      reset();
      setCodes(result.recovery_codes);
      await load();
    });
  };
  const disable = (event) => {
    event.preventDefault();
    run(async () => {
      await turnOffMfa({ password, code: code.trim() });
      reset();
      await load();
    });
  };

  const passwordField = (
    <label className="form-field">
      <span className="desk-line">
        <LineMark name="account" size={14} />
        Your password
      </span>
      <PasswordInput name="mfa-password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
    </label>
  );
  const codeField = (label) => (
    <label className="form-field">
      <span className="desk-line">
        <LineMark name="check" size={14} />
        {label}
      </span>
      <input value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" maxLength={11} required />
    </label>
  );

  return (
    <section className="card studio-panel account-mfa">
      <h2>
        <LineMark name="access" />
        Authenticator app
        {status ? (
          <span className={`account-mfa-state${status.enrolled ? ' is-on' : ''}`}>{status.enrolled ? 'On' : status.required ? 'Required' : 'Off'}</span>
        ) : null}
      </h2>
      <p className="account-mfa-lead">
        A second sign-in step for accounts that can see many students&apos; records: after the password, a 6-digit code
        from an app on your phone.
        {status?.enrolled ? ` Recovery codes left: ${status.recovery_codes_left}.` : ''}
      </p>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {codes ? (
        <div className="mfa-step">
          <RecoveryCodes codes={codes} />
          <button className="btn" type="button" onClick={() => setCodes(null)}>
            I saved them
          </button>
        </div>
      ) : null}

      {!codes && status && !status.enrolled && mode !== 'setup' ? (
        <button className="btn" type="button" onClick={() => reset('setup')}>
          Set up the authenticator app
        </button>
      ) : null}
      {!codes && status?.enrolled && !mode ? (
        <div className="account-password-foot">
          <button className="btn btn-secondary" type="button" onClick={() => reset('renew')}>
            New recovery codes
          </button>
          <button className="btn btn-secondary" type="button" onClick={() => reset('disable')}>
            Turn off
          </button>
        </div>
      ) : null}

      {mode === 'setup' && !setup ? (
        <form className="account-password-form" onSubmit={start}>
          {passwordField}
          <div className="account-password-foot">
            <button className="btn btn-ghost" type="button" onClick={() => reset()}>
              Cancel
            </button>
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Preparing…' : 'Continue'}
            </button>
          </div>
        </form>
      ) : null}
      {mode === 'setup' && setup ? (
        <form className="account-password-form" onSubmit={finish}>
          <div className="mfa-setup">
            <img
              className="mfa-qr"
              src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(setup.qr_svg)}`}
              alt="QR code for the authenticator app"
              width="176"
              height="176"
            />
            <p className="mfa-secret">
              Can&apos;t scan? Enter this key in the app:
              <code>{setup.secret.replace(/(.{4})/g, '$1 ').trim()}</code>
            </p>
          </div>
          {codeField('Code from the app')}
          <div className="account-password-foot">
            <button className="btn btn-ghost" type="button" onClick={() => reset()}>
              Cancel
            </button>
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Checking…' : 'Finish set-up'}
            </button>
          </div>
        </form>
      ) : null}
      {mode === 'renew' || mode === 'disable' ? (
        <form className="account-password-form" onSubmit={mode === 'renew' ? renew : disable}>
          {mode === 'disable' && status?.required ? (
            <p className="alert alert-info">Your role requires the app: you will be asked to set it up again at your next sign-in.</p>
          ) : null}
          {passwordField}
          {codeField('Code from the app (or a recovery code)')}
          <div className="account-password-foot">
            <button className="btn btn-ghost" type="button" onClick={() => reset()}>
              Cancel
            </button>
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Checking…' : mode === 'renew' ? 'Make new codes' : 'Turn off'}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
