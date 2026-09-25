import { useEffect, useMemo, useState } from 'react';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchPlacements, fetchSections, savePlacement, savePlacementsBulk } from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';

function matches(row, query) {
  if (!query) return true;
  const hay = [row.name, row.lrn, row.program_code, row.program_name, row.section].join(' ').toLowerCase();
  return hay.includes(query);
}

function matchingSections(row, sections, transfer = false) {
  return sections.filter((section) => {
    if (row.grade_level && section.grade_level && row.grade_level !== section.grade_level) return false;
    if (!transfer && row.program_code && section.program_code && row.program_code !== section.program_code) {
      return false;
    }
    return true;
  });
}

export default function HeadPlacePage() {
  const [view, setView] = useState('section');
  const [students, setStudents] = useState([]);
  const [sections, setSections] = useState([]);
  const [sectionId, setSectionId] = useState('');
  const [query, setQuery] = useState('');
  const [picks, setPicks] = useState({});
  const [selected, setSelected] = useState({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const [placementRows, sectionRows] = await Promise.all([fetchPlacements(), fetchSections()]);
    setStudents(placementRows);
    setSections(sectionRows);
    setSectionId((current) => current || (sectionRows[0] ? String(sectionRows[0].id) : ''));
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const section = sections.find((row) => String(row.id) === String(sectionId));
  const unplaced = students.filter((row) => !row.placed).length;

  const candidates = useMemo(() => {
    if (!section) return [];
    return students.filter((row) => {
      if (row.placed) return false;
      if (row.grade_level && section.grade_level && row.grade_level !== section.grade_level) return false;
      if (row.program_code && section.program_code && row.program_code !== section.program_code) return false;
      return matches(row, query.trim().toLowerCase());
    });
  }, [students, section, query]);

  const movers = useMemo(() => {
    return students.filter((row) => matches(row, query.trim().toLowerCase()));
  }, [students, query]);

  const chosen = candidates.filter((row) => selected[row.student_id]);

  async function placeBulk() {
    if (!section || chosen.length === 0) return;
    setBusy('bulk');
    setError('');
    setMessage('');
    try {
      const saved = await savePlacementsBulk({
        section: Number(sectionId),
        students: chosen.map((row) => row.student_id),
      });
      setSelected({});
      setMessage(`Placed ${saved.placed} student(s) in ${saved.section}.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function moveOne(row) {
    const nextId = picks[row.student_id] || matchingSections(row, sections)[0]?.id;
    if (!nextId) {
      setError('Create a matching section first.');
      return;
    }
    setBusy(`move-${row.student_id}`);
    setError('');
    setMessage('');
    try {
      const saved = await savePlacement({
        student: row.student_id,
        section: Number(nextId),
        transfer: Boolean(row.placed),
      });
      setMessage(`${row.name} ${row.placed ? 'transferred' : 'placed'} to ${saved.section}.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading placements…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Roster" title="Place students" icon="place">
        <p>Fill a section from the matching unplaced list, or transfer a placed student to another section or program.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{unplaced} unplaced</span>
          <span className="studio-chip">{students.length} active</span>
        </div>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        <button type="button" className={`studio-filter${view === 'section' ? ' is-active' : ''}`} onClick={() => setView('section')}>
          By section
        </button>
        <button type="button" className={`studio-filter${view === 'move' ? ' is-active' : ''}`} onClick={() => setView('move')}>
          Move one
        </button>
      </div>

      <label className="studio-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search
        </span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, LRN, or program" />
      </label>

      {view === 'section' ? (
        <div className="studio-grid is-wide">
          <section className="card studio-panel">
            <h2>
              <LineMark name="sections" />
              Sections
            </h2>
            <div className="studio-pick-list">
              {sections.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  className={`studio-pick${String(row.id) === String(sectionId) ? ' is-active' : ''}`}
                  onClick={() => setSectionId(String(row.id))}
                >
                  <strong className="desk-line">
                    <LineMark name="sections" size={14} />
                    {sectionLabel(row)}
                  </strong>
                  <em>{row.student_count || 0} placed</em>
                </button>
              ))}
            </div>
          </section>
          <section className="card studio-panel">
            <div className="studio-toolbar">
              <div>
                <h2 className="desk-line">
                  <LineMark name="sections" />
                  {section ? sectionLabel(section) : 'Select a section'}
                </h2>
                <p className="studio-empty">{candidates.length} matching unplaced</p>
              </div>
              <button className="btn" type="button" disabled={busy === 'bulk' || chosen.length === 0} onClick={placeBulk}>
                {busy === 'bulk' ? 'Placing…' : `Place selected (${chosen.length})`}
              </button>
            </div>
            {candidates.length === 0 ? <p className="studio-empty">No matching unplaced students.</p> : null}
            {candidates.map((row) => (
              <label className="studio-check" key={row.student_id}>
                <input
                  type="checkbox"
                  checked={Boolean(selected[row.student_id])}
                  onChange={(event) =>
                    setSelected((current) => ({ ...current, [row.student_id]: event.target.checked }))
                  }
                />
                <span>
                  <strong className="desk-line">
                    <LineMark name="user" size={14} />
                    {row.name}
                  </strong>
                  <em>
                    {row.lrn} · {row.program_code}
                  </em>
                </span>
              </label>
            ))}
          </section>
        </div>
      ) : (
        <section className="card studio-panel">
          {movers.length === 0 ? <p className="studio-empty">No students match that search.</p> : null}
          {movers.map((row) => {
            const options = matchingSections(row, sections, Boolean(row.placed));
            return (
              <article className="card studio-row is-place" key={row.student_id}>
                <div>
                  <h2>
                    <LineMark name="user" />
                    {row.name}
                  </h2>
                  <p>
                    {row.lrn} · {row.section || 'Not placed'}
                  </p>
                </div>
                <div className="studio-picks">
                  {options.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`studio-chip-btn${String(picks[row.student_id] || options[0]?.id) === String(item.id) ? ' is-active' : ''}`}
                      onClick={() => setPicks((current) => ({ ...current, [row.student_id]: item.id }))}
                    >
                      {sectionLabel(item)}
                    </button>
                  ))}
                </div>
                <button className="btn" type="button" disabled={busy === `move-${row.student_id}` || options.length === 0} onClick={() => moveOne(row)}>
                  {busy === `move-${row.student_id}` ? 'Saving…' : row.placed ? 'Transfer' : 'Place'}
                </button>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}
