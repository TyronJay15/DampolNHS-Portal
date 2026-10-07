import { useState } from 'react';
import { giveConsent } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

export default function ConsentPanel({ consent, onChange }) {
  const [agree, setAgree] = useState(false);
  const [guardian, setGuardian] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { notice, minor } = consent;
  const canSubmit = agree && (!minor || guardian) && !busy;

  async function submit(event) {
    event.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError('');
    try {
      onChange(await giveConsent({ kind: 'assessment', noticeVersion: notice.version, guardianConfirmed: guardian }));
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card gd-panel" aria-labelledby="gd-consent-title">
      <h2 id="gd-consent-title">Before you start: how your information is used</h2>
      <dl className="gd-facts">
        {notice.sections.map((section) => (
          <div key={section.title}>
            <dt>{section.title}</dt>
            <dd>{section.body}</dd>
          </div>
        ))}
      </dl>
      <form className="desk" onSubmit={submit}>
        <label className="gd-check" htmlFor="gd-agree">
          <input id="gd-agree" type="checkbox" checked={agree} onChange={(event) => setAgree(event.target.checked)} />
          <span>
            <strong>Required for the assessment.</strong> I have read how my grades, strand and answers are used to suggest
            college programs, and I know I can withdraw at any time.
          </span>
        </label>
        {minor ? (
          <label className="gd-check" htmlFor="gd-guardian">
            <input id="gd-guardian" type="checkbox" checked={guardian} onChange={(event) => setGuardian(event.target.checked)} />
            <span>
              <strong>Parent or guardian.</strong> Because you are under 18, or your birthdate is not on file, confirm that a
              parent or guardian agreed.
            </span>
          </label>
        ) : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <div className="gd-actions">
          <button className="btn" type="submit" disabled={!canSubmit}>
            {busy ? 'Saving…' : 'Agree and continue'}
          </button>
          <span className="gd-note">Notice version {notice.version}</span>
        </div>
      </form>
    </section>
  );
}
