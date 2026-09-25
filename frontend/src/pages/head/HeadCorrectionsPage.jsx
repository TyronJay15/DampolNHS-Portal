import { useEffect, useState } from 'react';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchCorrections, reviewCorrection } from '../../services/adminService';
import { when } from '../../utils/when';

export default function HeadCorrectionsPage() {
  const [tab, setTab] = useState('pending');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  async function load(nextTab = tab) {
    const data = await fetchCorrections(nextTab === 'record' ? 'record' : 'pending');
    setRows(data || []);
  }

  useEffect(() => {
    load('pending')
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function switchTab(next) {
    setTab(next);
    setLoading(true);
    setError('');
    try {
      await load(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function decide(row, status) {
    setBusyId(row.id);
    setError('');
    setMessage('');
    try {
      await reviewCorrection(row.id, { status });
      await load('pending');
      setMessage(`${status === 'approved' ? 'Approved' : 'Rejected'} correction for ${row.student}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <Loading label="Loading corrections…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Adjustments" title="Corrections" icon="corrections">
        <p>Pending requests wait here. Record keeps every approved or rejected change.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{rows.length} {tab === 'record' ? 'on record' : 'pending'}</span>
        </div>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        <button type="button" className={`studio-filter${tab === 'pending' ? ' is-active' : ''}`} onClick={() => switchTab('pending')}>
          Pending
        </button>
        <button type="button" className={`studio-filter${tab === 'record' ? ' is-active' : ''}`} onClick={() => switchTab('record')}>
          Record
        </button>
      </div>

      {rows.length === 0 ? (
        <p className="card studio-panel studio-empty">
          {tab === 'record' ? 'No reviewed corrections yet.' : 'No pending corrections.'}
        </p>
      ) : null}

      {rows.map((row) => (
        <article className="card studio-row is-stack" key={row.id}>
          <div>
            <p className="studio-kicker">{row.section} · {row.term}</p>
            <h2>
              <LineMark name="user" />
              {row.student} · {row.subject}
            </h2>
            <p>
              {row.current_score} → {row.proposed_score}
              {row.reason ? ` · ${row.reason}` : ''}
            </p>
            {tab === 'record' ? (
              <p>
                {row.status} · {row.reviewed_by || 'Reviewed'} · {when(row.reviewed_at)}
              </p>
            ) : (
              <p>Requested by {row.requested_by || 'teacher'} · {when(row.created_at)}</p>
            )}
          </div>
          {tab === 'pending' ? (
            <div className="studio-actions">
              <button className="btn" type="button" disabled={busyId === row.id} onClick={() => decide(row, 'approved')}>
                Approve
              </button>
              <button className="btn btn-secondary" type="button" disabled={busyId === row.id} onClick={() => decide(row, 'rejected')}>
                Reject
              </button>
            </div>
          ) : (
            <span className={`studio-status ${row.status === 'approved' ? 'is-approved' : ''}`}>
              <LineMark name={row.status === 'approved' ? 'approve' : 'corrections'} size={14} />
              {row.status}
            </span>
          )}
        </article>
      ))}
    </div>
  );
}
