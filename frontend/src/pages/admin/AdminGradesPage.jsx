import { useEffect, useState } from 'react';
import Loading from '../../components/Loading/Loading';
import { approveGrades, fetchCorrections, fetchGradeQueues, fetchSchoolYears, returnGrades, reviewCorrection, saveTermDeadline } from '../../services/adminService';
import { fetchTerms } from '../../services/teacherService';
import './AdminGradesPage.css';

function toInput(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function windowsFromTerms(termRows) {
  const next = {};
  termRows.forEach((term) => {
    next[term.id] = {
      encode_opens_at: toInput(term.encode_opens_at),
      encode_closes_at: toInput(term.encode_closes_at),
    };
  });
  return next;
}

export default function AdminGradesPage() {
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [groups, setGroups] = useState([]);
  const [busyKey, setBusyKey] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [windows, setWindows] = useState({});
  const [savingTerm, setSavingTerm] = useState('');
  const [corrections, setCorrections] = useState([]);

  useEffect(() => {
    fetchSchoolYears()
      .then((years) => {
        const current = years.find((year) => year.is_current) || years[0];
        if (!current) return [];
        return fetchTerms(current.id);
      })
      .then((termRows) => {
        setTerms(termRows);
        setWindows(windowsFromTerms(termRows));
        const current = termRows.find((row) => row.is_current) || termRows[0];
        setTermId(current ? String(current.id) : '');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!termId) return undefined;
    let cancelled = false;
    fetchGradeQueues(termId)
      .then((data) => {
        if (!cancelled) setGroups(data.groups || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [termId]);

  async function reload() {
    const [data, pending] = await Promise.all([
      fetchGradeQueues(termId),
      fetchCorrections('pending'),
    ]);
    setGroups(data.groups || []);
    setCorrections(pending || []);
  }

  useEffect(() => {
    fetchCorrections('pending')
      .then(setCorrections)
      .catch(() => {});
  }, []);

  async function runAction(group, action) {
    const key = `${action}-${group.section_id}-${group.subject_id}`;
    setBusyKey(key);
    setMessage('');
    setError('');
    try {
      const payload = { term: Number(termId), section: group.section_id, subject: group.subject_id };
      const result = action === 'approve' ? await approveGrades(payload) : await returnGrades(payload);
      await reload();
      if (action === 'approve') {
        setMessage(`Approved ${result.approved} grade(s).`);
      } else {
        setMessage(
          `Returned ${result.returned} hidden grade(s) to draft.` +
            (result.still_shown ? ` ${result.still_shown} shown card(s) left untouched.` : ''),
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  async function decideCorrection(row, status) {
    setMessage('');
    setError('');
    try {
      await reviewCorrection(row.id, { status });
      await reload();
      setMessage(`${status === 'approved' ? 'Approved' : 'Rejected'} correction for ${row.student}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveDeadline(term) {
    const draft = windows[term.id] || {};
    setSavingTerm(String(term.id));
    setMessage('');
    setError('');
    try {
      const saved = await saveTermDeadline(term.id, {
        encode_opens_at: toIso(draft.encode_opens_at),
        encode_closes_at: toIso(draft.encode_closes_at),
      });
      setTerms((rows) => rows.map((row) => (row.id === saved.id ? { ...row, ...saved } : row)));
      setWindows((current) => ({
        ...current,
        [saved.id]: {
          encode_opens_at: toInput(saved.encode_opens_at),
          encode_closes_at: toInput(saved.encode_closes_at),
        },
      }));
      setMessage(`Encode window saved for ${saved.label}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingTerm('');
    }
  }

  if (loading) return <Loading label="Loading grade queues…" />;

  return (
    <div className="admin-grades">
      <h1>Grades</h1>
      <p className="admin-lede">Set the encode window, then approve or return submitted classes. Advisers show the report card to students after every subject is approved.</p>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <section className="card admin-deadline-card">
        <h2>Encode deadlines</h2>
        {terms.map((term) => {
          const draft = windows[term.id] || { encode_opens_at: '', encode_closes_at: '' };
          return (
            <div className="admin-deadline-row" key={term.id}>
              <p className="admin-deadline-label">
                {term.label}
                {term.encode_open ? '' : ' · closed'}
              </p>
              <label className="form-field">
                Opens
                <input
                  type="datetime-local"
                  value={draft.encode_opens_at}
                  onChange={(event) =>
                    setWindows((current) => ({
                      ...current,
                      [term.id]: { ...draft, encode_opens_at: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="form-field">
                Closes
                <input
                  type="datetime-local"
                  value={draft.encode_closes_at}
                  onChange={(event) =>
                    setWindows((current) => ({
                      ...current,
                      [term.id]: { ...draft, encode_closes_at: event.target.value },
                    }))
                  }
                />
              </label>
              <button
                className="btn"
                type="button"
                disabled={savingTerm === String(term.id)}
                onClick={() => saveDeadline(term)}
              >
                {savingTerm === String(term.id) ? 'Saving…' : 'Save window'}
              </button>
            </div>
          );
        })}
      </section>
      {corrections.length ? (
        <section className="card admin-deadline-card">
          <h2>Pending corrections</h2>
          {corrections.map((row) => (
            <div className="admin-deadline-row" key={row.id}>
              <p className="admin-deadline-label">
                {row.student} · {row.subject}
                <br />
                {row.current_score} → {row.proposed_score}
              </p>
              <p>{row.reason}</p>
              <button className="btn" type="button" onClick={() => decideCorrection(row, 'approved')}>
                Approve
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => decideCorrection(row, 'rejected')}>
                Reject
              </button>
            </div>
          ))}
        </section>
      ) : null}
      <label className="form-field">
        Term
        <select value={termId} onChange={(event) => setTermId(event.target.value)}>
          {terms.map((term) => (
            <option key={term.id} value={term.id}>
              {term.label}
            </option>
          ))}
        </select>
      </label>
      {groups.length === 0 ? <p>No encoded grades for this term yet.</p> : null}
      <div className="admin-grade-list">
        {groups.map((group) => (
          <article className="card admin-grade-card" key={`${group.section_id}-${group.subject_id}`}>
            <h2>
              {group.subject} · {group.section}
            </h2>
            <p>
              Draft {group.draft} · Submitted {group.submitted} · Approved {group.approved} · Shown {group.released}
            </p>
            <div className="admin-grade-actions">
              <button
                className="btn"
                type="button"
                disabled={!group.submitted || busyKey.startsWith('approve')}
                onClick={() => runAction(group, 'approve')}
              >
                Approve submitted
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                disabled={(!group.submitted && !group.approved) || group.released || busyKey.startsWith('return')}
                onClick={() => runAction(group, 'return')}
              >
                Return to draft
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
