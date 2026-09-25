import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  archiveSchoolYear,
  createSchoolYear,
  deleteSchoolYear,
  fetchEncodeWindowHistory,
  fetchSchoolYears,
  saveSchoolYear,
  saveTermDeadline,
} from '../../services/adminService';
import { when } from '../../utils/when';
import { fetchTerms } from '../../services/teacherService';

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

export default function HeadYearPage() {
  const [years, setYears] = useState([]);
  const [terms, setTerms] = useState([]);
  const [label, setLabel] = useState('');
  const [windows, setWindows] = useState({});
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const yearRows = await fetchSchoolYears();
    setYears(yearRows);
    const current = yearRows.find((row) => row.is_current) || yearRows[0];
    if (!current) {
      setTerms([]);
      return;
    }
    const termRows = await fetchTerms(current.id);
    setTerms(termRows);
    const next = {};
    termRows.forEach((term) => {
      next[term.id] = {
        encode_opens_at: toInput(term.encode_opens_at),
        encode_closes_at: toInput(term.encode_closes_at),
      };
    });
    setWindows(next);
    setHistory(await fetchEncodeWindowHistory(current.id));
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    setBusy('create');
    setError('');
    setMessage('');
    try {
      await createSchoolYear({ label, is_current: years.length === 0 });
      setLabel('');
      setMessage(`Opened ${label}. Term 1–3 were created.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function makeCurrent(year) {
    setBusy(`year-${year.id}`);
    setError('');
    try {
      await saveSchoolYear(year.id, { is_current: true });
      setMessage(`${year.label} is now the current school year.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function archive(year) {
    setBusy(`archive-${year.id}`);
    setError('');
    setMessage('');
    try {
      await archiveSchoolYear(year.id);
      setMessage(`${year.label} moved to Archive with its sections and duties.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function remove(year) {
    setBusy(`delete-${year.id}`);
    setError('');
    setMessage('');
    try {
      await deleteSchoolYear(year.id);
      setMessage(`${year.label} deleted.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function saveWindow(term) {
    const draft = windows[term.id] || {};
    setBusy(`term-${term.id}`);
    setError('');
    try {
      const saved = await saveTermDeadline(term.id, {
        encode_opens_at: toIso(draft.encode_opens_at),
        encode_closes_at: toIso(draft.encode_closes_at),
      });
      setTerms((rows) => rows.map((row) => (row.id === saved.id ? { ...row, ...saved } : row)));
      const currentYear = years.find((row) => row.is_current);
      if (currentYear) setHistory(await fetchEncodeWindowHistory(currentYear.id));
      setMessage(`Encode window saved for ${saved.label}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading school years…" />;

  const current = years.find((row) => row.is_current);

  return (
    <div className="desk studio">
      <PageHead kicker="Calendar" title="School year & terms" icon="year">
        <p>Open a year to create Term 1–3. Archive parks it. Delete only an empty year that is not current.</p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-grid">
        <section className="card studio-panel">
          <h2>
            <LineMark name="year" />
            Open a year
          </h2>
          <form className="studio-form" onSubmit={handleCreate}>
            <label className="form-field is-wide">
              <span className="desk-line">
                <LineMark name="year" size={14} />
                Label
              </span>
              <input required placeholder="2026-2027" value={label} onChange={(event) => setLabel(event.target.value)} />
            </label>
            <div className="studio-form-actions">
              <button className="btn" type="submit" disabled={Boolean(busy)}>
                {busy === 'create' ? 'Opening…' : 'Open school year'}
              </button>
            </div>
          </form>
        </section>

        <section className="card studio-panel">
          <h2>
            <LineMark name="year" />
            Years
          </h2>
          {years.length === 0 ? <p className="studio-empty">No school year yet.</p> : null}
          <div className="studio-cards">
            {years.map((year) => (
              <article className="card studio-card" key={year.id}>
                <p className="studio-kicker">{year.is_current ? 'Current' : 'Ready'}</p>
                <h2>
                  <DeskMark name="year" size={16} />
                  {year.label}
                </h2>
                <div className="studio-actions">
                  {year.is_current ? null : (
                    <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => makeCurrent(year)}>
                      {busy === `year-${year.id}` ? 'Saving…' : 'Make current'}
                    </button>
                  )}
                  {year.is_current ? null : (
                    <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => archive(year)}>
                      {busy === `archive-${year.id}` ? 'Archiving…' : 'Archive'}
                    </button>
                  )}
                  {year.can_delete ? (
                    <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => remove(year)}>
                      {busy === `delete-${year.id}` ? 'Deleting…' : 'Delete empty'}
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="card studio-panel">
        <h2>
          <LineMark name="year" />
          Encode windows {current ? `· ${current.label}` : ''}
        </h2>
        {terms.length === 0 ? <p className="studio-empty">Open a school year to get Term 1–3.</p> : null}
        {terms.map((term) => {
          const draft = windows[term.id] || { encode_opens_at: '', encode_closes_at: '' };
          return (
            <div className="studio-row is-windows" key={term.id}>
              <div>
                <h2>
                  <LineMark name="year" />
                  {term.label}
                </h2>
                <p>{term.encode_open ? 'Encode open' : 'Encode closed'}</p>
              </div>
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="year" size={14} />
                  Opens
                </span>
                <input
                  type="datetime-local"
                  value={draft.encode_opens_at}
                  onChange={(event) =>
                    setWindows((currentWindows) => ({
                      ...currentWindows,
                      [term.id]: { ...draft, encode_opens_at: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="year" size={14} />
                  Closes
                </span>
                <input
                  type="datetime-local"
                  value={draft.encode_closes_at}
                  onChange={(event) =>
                    setWindows((currentWindows) => ({
                      ...currentWindows,
                      [term.id]: { ...draft, encode_closes_at: event.target.value },
                    }))
                  }
                />
              </label>
              <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => saveWindow(term)}>
                {busy === `term-${term.id}` ? 'Saving…' : 'Save window'}
              </button>
            </div>
          );
        })}
      </section>

      <section className="card studio-panel">
        <h2>
          <LineMark name="history" />
          Window history {current ? `· ${current.label}` : ''}
        </h2>
        {history.length === 0 ? (
          <p className="studio-empty">Saved encode windows will appear here.</p>
        ) : (
          <div className="studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  <th>Term</th>
                  <th>Opens</th>
                  <th>Closes</th>
                  <th>Changed by</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.id}>
                    <td>{row.term}</td>
                    <td>{when(row.opens_at) || '—'}</td>
                    <td>{when(row.closes_at) || '—'}</td>
                    <td>{row.changed_by || '—'}</td>
                    <td>{when(row.changed_at) || '—'}</td>
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
