import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  archiveSection,
  createSection,
  fetchPrograms,
  fetchSchoolYears,
  fetchSections,
} from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';

const STATUS_LABEL = {
  draft: 'Draft',
  in_progress: 'In progress',
  ready: 'Ready',
  active: 'Active',
};

function statusClass(status) {
  if (status === 'active') return 'is-approved';
  if (status === 'ready') return 'is-ready';
  if (status === 'in_progress') return 'is-submitted';
  return '';
}

export default function HeadSectionManagePage() {
  const [years, setYears] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [sections, setSections] = useState([]);
  const [yearId, setYearId] = useState('');
  const [gradeFilter, setGradeFilter] = useState('');
  const [programFilter, setProgramFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [query, setQuery] = useState('');
  const [form, setForm] = useState({ name: '', grade_level: 'Grade 11', program: '', school_year: '', capacity: 40 });
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const [yearRows, programRows, sectionRows] = await Promise.all([
      fetchSchoolYears(),
      fetchPrograms(),
      fetchSections(yearId ? { school_year: yearId } : {}),
    ]);
    setYears(yearRows);
    setPrograms(programRows);
    setSections(sectionRows);
    const current = yearRows.find((row) => row.is_current) || yearRows[0];
    setYearId((currentId) => currentId || (current ? String(current.id) : ''));
    setForm((currentForm) => {
      const grade = currentForm.grade_level || 'Grade 11';
      const gradePrograms = programRows.filter((row) => row.grade_level === grade);
      const stillValid = gradePrograms.some((row) => String(row.id) === currentForm.program);
      return {
        ...currentForm,
        school_year: currentForm.school_year || (current ? String(current.id) : ''),
        program: stillValid ? currentForm.program : gradePrograms[0] ? String(gradePrograms[0].id) : '',
      };
    });
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!yearId || loading) return undefined;
    let cancelled = false;
    fetchSections({ school_year: yearId })
      .then((rows) => {
        if (!cancelled) setSections(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [yearId, loading]);

  const gradePrograms = useMemo(
    () => programs.filter((row) => row.grade_level === form.grade_level),
    [programs, form.grade_level],
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return sections.filter((row) => {
      if (gradeFilter && row.grade_level !== gradeFilter) return false;
      if (programFilter && String(row.program) !== programFilter && row.program_code !== programFilter) return false;
      if (statusFilter && row.status !== statusFilter) return false;
      if (!needle) return true;
      const hay = [row.name, row.display_label, row.program_code, row.grade_level].join(' ').toLowerCase();
      return hay.includes(needle);
    });
  }, [sections, gradeFilter, programFilter, statusFilter, query]);

  async function handleCreate(event) {
    event.preventDefault();
    setBusy('create');
    setError('');
    setMessage('');
    try {
      const saved = await createSection({
        name: form.name,
        grade_level: form.grade_level,
        program: Number(form.program) || null,
        school_year: Number(form.school_year),
        capacity: Number(form.capacity) || 40,
      });
      setForm((current) => ({ ...current, name: '' }));
      setMessage(`${saved.display_label} created. Find it in All Sections below.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function confirmArchive() {
    if (!archiveTarget) return;
    setBusy(`archive-${archiveTarget.id}`);
    setError('');
    try {
      await archiveSection(archiveTarget.id);
      setMessage(`${sectionLabel(archiveTarget)} archived. It now appears under Archive → Sections.`);
      setArchiveTarget(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading section management…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Sectioning" title="Section management" icon="sections">
        <p>Create sections, search the directory, and open setup. Archive removes a section from this list without deleting history.</p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <section className="card studio-panel studio-compact-create">
        <h2>
          <LineMark name="sections" />
          Create section
        </h2>
        <form className="studio-inline-form" onSubmit={handleCreate}>
          <label className="form-field">
            <span>Name</span>
            <input required placeholder="A" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="form-field">
            <span>Capacity</span>
            <input type="number" min="1" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
          </label>
          <label className="form-field">
            <span>Year</span>
            <select value={form.school_year} onChange={(e) => setForm({ ...form, school_year: e.target.value })}>
              {years.map((year) => (
                <option key={year.id} value={year.id}>{year.label}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Grade</span>
            <select
              value={form.grade_level}
              onChange={(e) => {
                const grade = e.target.value;
                const next = programs.filter((row) => row.grade_level === grade);
                setForm({ ...form, grade_level: grade, program: next[0] ? String(next[0].id) : '' });
              }}
            >
              <option>Grade 11</option>
              <option>Grade 12</option>
            </select>
          </label>
          <label className="form-field">
            <span>Program</span>
            <select value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })}>
              {gradePrograms.map((row) => (
                <option key={row.id} value={row.id}>{row.code}</option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit" disabled={Boolean(busy)}>{busy === 'create' ? 'Saving…' : 'Create'}</button>
        </form>
      </section>

      <section className="card studio-panel studio-directory">
        <div className="studio-directory-head">
          <div>
            <h2>
              <LineMark name="sections" />
              All sections
            </h2>
            <p className="studio-empty">{filtered.length} section(s) in this directory</p>
          </div>
          <label className="studio-search studio-search-wide">
            <span>Search sections</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name, program, or grade" />
          </label>
        </div>
        <div className="studio-toolbar studio-toolbar-filter">
          <label className="form-field">
            <span>School year</span>
            <select value={yearId} onChange={(e) => setYearId(e.target.value)}>
              {years.map((year) => (
                <option key={year.id} value={year.id}>{year.label}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Grade</span>
            <select value={gradeFilter} onChange={(e) => setGradeFilter(e.target.value)}>
              <option value="">All</option>
              <option>Grade 11</option>
              <option>Grade 12</option>
            </select>
          </label>
          <label className="form-field">
            <span>Program</span>
            <select value={programFilter} onChange={(e) => setProgramFilter(e.target.value)}>
              <option value="">All</option>
              {programs.map((row) => (
                <option key={row.id} value={row.id}>{row.code}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All</option>
              {Object.entries(STATUS_LABEL).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        {filtered.length === 0 ? (
          <p className="studio-empty studio-empty-pad">No sections match. Create one above or adjust filters.</p>
        ) : (
          <div className="studio-table-wrap">
            <table className="studio-table studio-table-directory">
              <thead>
                <tr>
                  <th>Section</th>
                  <th>Program</th>
                  <th>Students</th>
                  <th>Progress</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <strong>{sectionLabel(row)}</strong>
                      <p className="studio-table-sub">{row.school_year_label}</p>
                    </td>
                    <td>{row.program_code}</td>
                    <td>{row.student_count || 0}{row.capacity ? ` / ${row.capacity}` : ''}</td>
                    <td>
                      <div className="studio-progress studio-progress-inline">
                        <div className="studio-progress-bar" style={{ width: `${row.progress_percent || 0}%` }} />
                      </div>
                      <span className="studio-table-sub">{row.progress_percent || 0}%</span>
                    </td>
                    <td>
                      <span className={`studio-status ${statusClass(row.status)}`}>{STATUS_LABEL[row.status] || row.status}</span>
                    </td>
                    <td>
                      <div className="studio-actions">
                        <Link className="btn" to={`/head/sections/${row.id}/setup`}>
                          {row.status === 'active' ? 'View' : 'Setup'}
                        </Link>
                        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => setArchiveTarget(row)}>
                          Archive
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="studio-advanced-links">
          <p className="studio-kicker">Advanced tools</p>
          <div className="studio-actions">
            <Link className="btn btn-secondary" to="/head/place">Place students</Link>
            <Link className="btn btn-secondary" to="/head/assign">Assign teachers</Link>
          </div>
        </div>
      </section>

      {archiveTarget ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Archive section</h2>
            <p>
              Archive <strong>{sectionLabel(archiveTarget)}</strong>? It will leave this list and appear under Archive → Sections.
              Student and grade history stay protected.
            </p>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setArchiveTarget(null)}>Cancel</button>
              <button className="btn" type="button" onClick={confirmArchive} disabled={busy === `archive-${archiveTarget.id}`}>
                {busy === `archive-${archiveTarget.id}` ? 'Archiving…' : 'Archive section'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
