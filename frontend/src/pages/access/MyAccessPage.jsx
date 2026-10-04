import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import RequestChanges from '../../components/Access/RequestChanges';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchAccessOverview, fetchAccessRequests, withdrawAccessRequest } from '../../services/accessService';
import { when } from '../../utils/when';
import './AccessPage.css';

const STATUS_CLASS = { pending: 'is-progress', approved: 'is-approved', failed: 'is-progress' };

function untilLabel(value) {
  if (!value) return 'No end date';
  return `Until ${new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' })}`;
}

// The tagged person's side: what they may prepare, and what happened to each request they sent.
export default function MyAccessPage() {
  const confirm = useConfirm();
  const [overview, setOverview] = useState(null);
  const [requests, setRequests] = useState([]);
  const [busy, setBusy] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [summary, mine] = await Promise.all([fetchAccessOverview(), fetchAccessRequests('mine')]);
    setOverview(summary);
    setRequests(mine);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  if (!overview) return error ? <p className="alert alert-error">{error}</p> : <Loading label="Loading your access…" />;

  async function withdraw(row) {
    const answer = await confirm({
      title: 'Withdraw this request?',
      body: row.summary,
      confirmLabel: 'Withdraw request',
      tone: 'warning',
    });
    if (!answer) return;
    setBusy(row.id);
    setError('');
    try {
      await withdrawAccessRequest(row.id);
      await load();
      setMessage('Request withdrawn.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(0);
    }
  }

  return (
    <div className="desk studio">
      <PageHead kicker="Delegation" title="My access" icon="access">
        <p>
          Work you were tagged to prepare. Each request waits for the owner&apos;s approval before anything changes.
        </p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      {overview.holds.length === 0 ? (
        <p className="card studio-panel studio-empty">You have no active tags right now.</p>
      ) : (
        <div className="acc-held">
          {overview.holds.map((tag) => (
            <article className="card studio-panel" key={tag.id}>
              <h2>
                <LineMark name="access" />
                {tag.activity_label}
              </h2>
              <p className="acc-meta">
                From {tag.granted_by ? `${tag.granted_by.name} (${tag.granted_by.role_label})` : 'the owner'} ·{' '}
                {tag.scope_text} · {untilLabel(tag.ends_on)}
              </p>
              {tag.note ? <p className="acc-note">{tag.note}</p> : null}
              <Link className="btn" to={tag.work_path}>
                Open
              </Link>
            </article>
          ))}
        </div>
      )}

      <section className="card studio-panel acc-requests">
        <h2>
          <LineMark name="history" />
          My requests
        </h2>
        {requests.length === 0 ? (
          <p className="studio-empty">Requests you submit will appear here.</p>
        ) : (
          <div className="studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Status</th>
                  <th>Sent</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {requests.map((row) => (
                  <tr key={row.id}>
                    <td className="acc-wrap">
                      {row.summary}
                      <p className="studio-table-sub">{row.activity_label}</p>
                      <RequestChanges changes={row.changes} />
                    </td>
                    <td>
                      <span className={`studio-chip ${STATUS_CLASS[row.status] || 'is-wait'}`}>{row.status_label}</span>
                      {row.decision_note || row.result?.error ? (
                        <p className="studio-table-sub">{row.result?.error || row.decision_note}</p>
                      ) : null}
                    </td>
                    <td>{when(row.created_at)}</td>
                    <td>
                      {row.can_withdraw ? (
                        <button
                          className="btn btn-secondary"
                          type="button"
                          disabled={Boolean(busy)}
                          onClick={() => withdraw(row)}
                        >
                          {busy === row.id ? 'Withdrawing…' : 'Withdraw'}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
