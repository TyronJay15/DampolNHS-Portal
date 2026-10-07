import { useEffect, useState } from 'react';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { formatDate } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import MetricStrip from '../../../components/MetricStrip/MetricStrip';
import { fetchOutcomes, fetchRecommenderStatus, validateOutcome } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

const VIEWS = [
  { value: 'recorded', label: 'Waiting for validation' },
  { value: 'validated', label: 'Validated' },
];

const EMPTY = {
  recorded: 'Nothing is waiting. Advisers record the program each graduate entered from their advisory page.',
  validated: 'No validated outcomes yet. Advisers record the program each graduate entered; a second person confirms it.',
};

// A second person confirms each outcome an adviser records. This is a school record, not training data.
export default function GuidanceOutcomesPage() {
  const confirm = useConfirm();
  const [view, setView] = useState('recorded');
  // Rows for one tab; another tab means the list is still loading.
  const [result, setResult] = useState({ view: null, rows: [] });
  // Exact totals from the recommender status (the lists stop at 200 rows).
  const [counts, setCounts] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(0);

  useEffect(() => {
    fetchRecommenderStatus()
      .then((data) => setCounts({ recorded: data.totals.outcomes_recorded, validated: data.totals.outcomes_validated }))
      .catch(() => setCounts(null));
  }, []);

  useEffect(() => {
    fetchOutcomes(view)
      .then((data) => setResult({ view, rows: data.outcomes }))
      .catch((err) => {
        setResult({ view, rows: [] });
        setError(err.message);
      });
  }, [view]);

  const rows = result.view === view ? result.rows : null;

  async function validate(row) {
    const answer = await confirm({
      title: `Validate ${row.student}'s outcome?`,
      body: 'Confirm that the graduate actually entered this program. A validated outcome can no longer be changed.',
      confirmLabel: 'Validate',
      facts: [
        { label: 'Program', value: row.program },
        { label: 'Recorded by', value: row.recorded_by || '—' },
      ],
    });
    if (!answer) return;
    setBusy(row.id);
    setError('');
    try {
      await validateOutcome(row.id);
      setResult((current) => ({ ...current, rows: current.rows.filter((item) => item.id !== row.id) }));
      setCounts((current) => (current ? { recorded: current.recorded - 1, validated: current.validated + 1 } : current));
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(0);
    }
  }

  return (
    <>
      {counts ? (
        <MetricStrip
          items={[
            { key: 'recorded', label: 'Waiting for validation', value: counts.recorded, icon: 'history', tone: 'gold' },
            { key: 'validated', label: 'Validated', value: counts.validated, icon: 'check', tone: 'green' },
          ]}
        />
      ) : null}
      <p className="gd-rule">
        <strong>Two-person rule.</strong> The person who records a graduate&apos;s program cannot validate it; someone
        else confirms it. This is a school record of where graduates went. It does not change student matches.
      </p>
      <div className="studio-tabs gd-count-tabs" role="tablist" aria-label="Outcome status">
        {VIEWS.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={view === item.value}
            className={view === item.value ? 'is-active' : ''}
            onClick={() => setView(item.value)}
          >
            {item.label}
            {counts ? <em>{counts[item.value]}</em> : null}
          </button>
        ))}
      </div>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {rows ? null : <Loading label="Loading outcomes…" />}
      {rows && !rows.length ? <p className="card gd-panel gd-note">{EMPTY[view]}</p> : null}
      {rows && rows.length ? (
        <div className="card studio-table-wrap">
          <table className="studio-table gd-table">
            <thead>
              <tr>
                <th scope="col">Graduate</th>
                <th scope="col">Program entered</th>
                <th scope="col">School year</th>
                <th scope="col">Recorded</th>
                <th scope="col">
                  <span className="gd-sr">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className={view === 'recorded' && row.can_validate ? 'gd-row-actionable' : undefined}>
                  <td>
                    <strong>{row.student}</strong>
                  </td>
                  <td>{row.program}</td>
                  <td>{row.school_year}</td>
                  <td>
                    {formatDate(row.recorded_at)} · {row.recorded_by || '—'}
                  </td>
                  <td>
                    {view === 'recorded' ? (
                      row.can_validate ? (
                        <button className="btn" type="button" disabled={busy === row.id} onClick={() => validate(row)}>
                          {busy === row.id ? 'Validating…' : 'Validate'}
                        </button>
                      ) : (
                        <span className="gd-note">Recorded by you; another person validates.</span>
                      )
                    ) : (
                      <span className="gd-pill is-ok">Validated</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
