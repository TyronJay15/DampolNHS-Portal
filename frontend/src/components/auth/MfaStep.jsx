import { useEffect, useState } from 'react';
import { confirmMfaEnrollment, startMfaEnrollment, verifyMfa } from '../../services/session';
import RecoveryCodes from './RecoveryCodes';
import './MfaStep.css';

function problem(err) {
  if (err.code === 'challenge_invalid') return { message: err.message, restart: true };
  return { message: err.message, restart: false };
}

/** The authenticator step of a sign-in: enter a code ('verify'), or set up the app first ('enroll').
 * Calls onDone(user) when signed in, onRestart() when the person must enter the password again. */
export default function MfaStep({ step, challenge, onDone, onRestart }) {
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(null);

  useEffect(() => {
    if (step !== 'enroll') return undefined;
    let cancelled = false;
    startMfaEnrollment(challenge)
      .then((data) => {
        if (!cancelled) setSetup(data);
      })
      .catch((err) => {
        if (!cancelled) setError(problem(err).message);
      });
    return () => {
      cancelled = true;
    };
  }, [step, challenge]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (step === 'verify') {
        onDone(await verifyMfa(challenge, code.trim()));
        return;
      }
      setFinished(await confirmMfaEnrollment(challenge, code.trim()));
    } catch (err) {
      const { message, restart } = problem(err);
      setError(message);
      setCode('');
      if (restart) onRestart(message);
    } finally {
      setBusy(false);
    }
  }

  if (finished) {
    return (
      <div className="mfa-step">
        <RecoveryCodes codes={finished.recoveryCodes} />
        <button className="btn" type="button" onClick={() => onDone(finished.user)}>
          I saved my recovery codes · Continue
        </button>
      </div>
    );
  }

  return (
    <form className="mfa-step" onSubmit={submit}>
      {step === 'enroll' ? (
        <>
          <p className="mfa-lead">
            Your account needs an authenticator app (Google Authenticator, Microsoft Authenticator or similar). Scan
            this code with the app, then type the 6-digit code it shows.
          </p>
          {setup ? (
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
          ) : !error ? (
            <p className="mfa-lead">Preparing your set-up…</p>
          ) : null}
        </>
      ) : (
        <p className="mfa-lead">Open your authenticator app and type the 6-digit code for the Dampol 1st NHS Portal.</p>
      )}
      {error ? <p className="alert alert-error">{error}</p> : null}
      <label className="form-field">
        {step === 'verify' ? 'Authenticator code or recovery code' : 'Code from the app'}
        <input
          type="text"
          inputMode={step === 'verify' ? 'text' : 'numeric'}
          autoComplete="one-time-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          maxLength={11}
          required
          autoFocus
        />
        {step === 'verify' ? <span className="auth-hint">Lost your phone? Use one of your recovery codes.</span> : null}
      </label>
      <button className="btn" type="submit" disabled={busy || (step === 'enroll' && !setup)}>
        {busy ? 'Checking…' : step === 'verify' ? 'Verify and sign in' : 'Finish set-up'}
      </button>
      <button className="mfa-back" type="button" onClick={() => onRestart('')}>
        ← Use a different account
      </button>
    </form>
  );
}
