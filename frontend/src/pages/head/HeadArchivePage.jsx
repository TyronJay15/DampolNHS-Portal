import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchArchive, restoreAssignment, restoreSchoolYear, restoreSection } from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';
import { when } from '../../utils/when';

const TABS = [
  { id: 'years', label: 'Years' },
  { id: 'sections', label: 'Sections' },
  { id: 'duties', label: 'Duties' },
];

export default function HeadArchivePage() {
  const [tab, setTab] = useState('years');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load(kind = tab) {
    const data = await fetchArchive(kind);
    setRows(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    load('years')
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

  async function restore(row) {
    setBusy(String(row.id));
    setError('');
    setMessage('');
    try {
      if (tab === 'years') {
        const saved = await restoreSchoolYear(row.id);
        setMessage(`${saved.label} is live again.`);
      } else if (tab === 'sections') {
        const saved = await restoreSection(row.id);
        setMessage(`${saved.display_label} is live again.`);
      } else {
        await restoreAssignment(row.id);
        setMessage(`${row.teacher} duty restored.`);
      }
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading archive…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Vault" title="Archive" icon="archive">
        <p>Years, sections, and ended duties stay here. Restore only if the slot is free.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{rows.length} parked</span>
        </div>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`studio-filter${tab === item.id ? ' is-active' : ''}`}
            onClick={() => switchTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? <p className="card studio-panel studio-empty">Nothing archived in this list.</p> : null}

      <div className="studio-cards">
        {rows.map((row) => (
          <article className="card studio-card" key={row.id}>
            <p className="studio-kicker">
              {tab === 'years' ? 'School year' : tab === 'sections' ? row.school_year_label : row.school_year}
            </p>
            <h2>
              <DeskMark name={tab === 'years' ? 'year' : tab === 'sections' ? 'sections' : 'assign'} size={16} />
              {tab === 'years'
                ? row.label
                : tab === 'sections'
                  ? sectionLabel(row)
                  : `${row.teacher} · ${row.type === 'adviser' ? 'Adviser' : row.subject}`}
            </h2>
            <p className="studio-empty">
              {tab === 'duties'
                ? `${row.section} · ended ${when(row.ended_at)}`
                : tab === 'sections'
                  ? `${row.student_count || 0} students parked with this section`
                  : `Archived ${when(row.archived_at)}`}
            </p>
            <div className="studio-actions">
              <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => restore(row)}>
                {busy === String(row.id) ? 'Restoring…' : 'Restore'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
