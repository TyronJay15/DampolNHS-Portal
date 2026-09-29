import { useEffect, useMemo, useState } from 'react';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchCorrections, reviewCorrection } from '../../services/adminService';
import { when } from '../../utils/when';

export default function HeadCorrectionsPage() {
  const [tab, setTab] = useState('pending');
  const [rows, setRows] = useState([]);
  const [openTeachers, setOpenTeachers] = useState({});
  const [note, setNote] = useState('');
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

  const grouped = useMemo(() => {
    const map = {};
    rows.forEach((row) => {
      const key = row.requested_by || 'Teacher';
      map[key] = map[key] || [];
      map[key].push(row);
    });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
  }, [rows]);

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
      await reviewCorrection(row.id, { status, note });
      await load('pending');
      setNote('');
      setMessage(`${status === 'approved' ? 'Approved' : 'Declined'} correction for ${row.student}. Teacher is notified.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <Loading label="Loading corrections…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Adjustments" title="Corrections" icon="corrections">
        <p>Grouped by teacher. Expand a card to review requests. Teachers receive the decision notification.</p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        <button type="button" className={`studio-filter${tab === 'pending' ? ' is-active' : ''}`} onClick={() => switchTab('pending')}>Pending</button>
        <button type="button" className={`studio-filter${tab === 'record' ? ' is-active' : ''}`} onClick={() => switchTab('record')}>Record</button>
      </div>

      {rows.length === 0 ? (
        <p className="card studio-panel studio-empty">No corrections in this list.</p>
      ) : (
        <div className="studio-accordion-list">
          {grouped.map(([teacher, items]) => {
            const open = Boolean(openTeachers[teacher]);
            return (
              <article className={`card studio-panel studio-accordion-card${open ? ' is-open' : ''}`} key={teacher}>
                <button type="button" className="studio-accordion-head" onClick={() => setOpenTeachers((c) => ({ ...c, [teacher]: !c[teacher] }))}>
                  <div>
                    <p className="studio-kicker">Teacher</p>
                    <h2>
                      <LineMark name="staff" />
                      {teacher}
                    </h2>
                    <p className="studio-empty">{items.length} correction(s)</p>
                  </div>
                  <span className="studio-accordion-caret">{open ? '▾' : '▸'}</span>
                </button>
                {open ? (
                  <div className="studio-accordion-body">
                    {items.map((row) => (
                      <article className="studio-correction-row" key={row.id}>
                        <div>
                          <p className="studio-kicker">{row.section} · {row.term}</p>
                          <h3>{row.student} · {row.subject}</h3>
                          <p>{row.current_score} → {row.proposed_score}{row.reason ? ` · ${row.reason}` : ''}</p>
                          {tab === 'record' ? (
                            <p className="studio-table-sub">{row.status} · {when(row.reviewed_at)}</p>
                          ) : (
                            <p className="studio-table-sub">{when(row.created_at)}</p>
                          )}
                          {row.approve_blocked ? <p className="alert alert-error">{row.approve_block_reason}</p> : null}
                        </div>
                        {tab === 'pending' ? (
                          <div className="studio-stack">
                            <input className="studio-textfield" type="text" placeholder="Decline note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
                            <div className="studio-actions">
                              <button className="btn" type="button" disabled={busyId === row.id || row.approve_blocked} onClick={() => decide(row, 'approved')}>Approve</button>
                              <button className="btn btn-secondary" type="button" disabled={busyId === row.id} onClick={() => decide(row, 'rejected')}>Decline</button>
                            </div>
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
