import { useState } from 'react';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { deleteGuidanceData, withdrawConsent } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';
import { formatDate } from '../../../components/Guidance/guidanceText';

export default function PrivacyControls({ consent, onChange }) {
  const confirm = useConfirm();
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  async function run(kind, request) {
    setBusy(kind);
    setError('');
    try {
      onChange(await request());
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy('');
    }
  }

  async function withdrawAll() {
    const answer = await confirm({
      title: 'Withdraw your consent?',
      body: 'Your assessment answers and saved recommendations are deleted. You will still see a limited match from your grades, and you can agree again later.',
      confirmLabel: 'Withdraw and delete',
      warning: 'This cannot be undone.',
    });
    if (answer) await run('withdraw', () => withdrawConsent('assessment'));
  }

  async function deleteAnswers() {
    const answer = await confirm({
      title: 'Delete your answers?',
      body: 'Your assessment answers and saved recommendations are deleted. Your consent stays, so you can take the assessment again.',
      confirmLabel: 'Delete answers',
      warning: 'This cannot be undone.',
    });
    if (answer) await run('delete', deleteGuidanceData);
  }

  return (
    <section className="card gd-panel" aria-labelledby="gd-privacy-title">
      <h2 id="gd-privacy-title">Your privacy choices</h2>
      <dl className="gd-facts">
        <div>
          <dt>Assessment and recommendations</dt>
          <dd>{consent.assessment ? `Agreed ${formatDate(consent.assessment.given_at)}` : 'Not agreed'}</dd>
        </div>
      </dl>
      {error ? <p className="alert alert-error">{error}</p> : null}
      <div className="gd-actions">
        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={deleteAnswers}>
          Delete my answers
        </button>
        <button className="btn btn-danger" type="button" disabled={Boolean(busy)} onClick={withdrawAll}>
          Withdraw consent
        </button>
      </div>
    </section>
  );
}
