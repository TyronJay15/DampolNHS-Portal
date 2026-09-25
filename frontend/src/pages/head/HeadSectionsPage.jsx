import { useEffect, useMemo, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  archiveSection,
  createSection,
  deleteSection,
  fetchPrograms,
  fetchSchoolYears,
  fetchSectionRoster,
  fetchSections,
  saveSection,
} from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';

export default function HeadSectionsPage() {
  const [years, setYears] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [sections, setSections] = useState([]);
  const [form, setForm] = useState({ name: '', grade_level: 'Grade 11', program: '', school_year: '' });
  const [selectedId, setSelectedId] = useState('');
  const [roster, setRoster] = useState([]);
  const [editName, setEditName] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const [yearRows, programRows, sectionRows] = await Promise.all([
      fetchSchoolYears(),
      fetchPrograms(),
      fetchSections(),
    ]);
    setYears(yearRows);
    setPrograms(programRows);
    setSections(sectionRows);
    const current = yearRows.find((row) => row.is_current) || yearRows[0];
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
    return sectionRows;
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const gradePrograms = useMemo(
    () => programs.filter((row) => row.grade_level === form.grade_level),
    [programs, form.grade_level],
  );

  const selected = sections.find((row) => String(row.id) === String(selectedId));
  const previewProgram = programs.find((row) => String(row.id) === String(form.program));
  const preview = sectionLabel({
    grade_level: form.grade_level,
    program_code: previewProgram?.code || '',
    name: form.name || 'A',
  });

  async function openRoster(row) {
    setSelectedId(String(row.id));
    setEditName(row.name);
    setBusy(`roster-${row.id}`);
    setError('');
    try {
      const data = await fetchSectionRoster(row.id);
      setRoster(data.students || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

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
      });
      setForm((current) => ({ ...current, name: '' }));
      setMessage(`${saved.display_label} opened.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function saveName() {
    if (!selected) return;
    setBusy('rename');
    setError('');
    setMessage('');
    try {
      const saved = await saveSection(selected.id, { name: editName });
      setMessage(`${saved.display_label} updated.`);
      const rows = await load();
      const next = rows.find((row) => row.id === selected.id);
      if (next) setEditName(next.name);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function archive(row) {
    setBusy(`archive-${row.id}`);
    setError('');
    setMessage('');
    try {
      await archiveSection(row.id);
      setMessage(`${sectionLabel(row)} moved to Archive.`);
      if (String(selectedId) === String(row.id)) {
        setSelectedId('');
        setRoster([]);
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function remove(row) {
    setBusy(`delete-${row.id}`);
    setError('');
    setMessage('');
    try {
      await deleteSection(row.id);
      setMessage(`${sectionLabel(row)} deleted.`);
      if (String(selectedId) === String(row.id)) {
        setSelectedId('');
        setRoster([]);
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading sections…" />;

  const grouped = {};
  sections.forEach((row) => {
    const key = `${row.grade_level || 'Grade'} · ${row.program_code || 'Program'}`;
    grouped[key] = grouped[key] || [];
    grouped[key].push(row);
  });

  return (
    <div className="desk studio">
      <PageHead kicker="Roster frame" title="Sections" icon="sections">
        <p>Type only the short name. The desk shows 11 - STEM A. Click a card for the roster.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{sections.length} live</span>
        </div>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-grid">
        <section className="card studio-panel">
          <h2>
            <LineMark name="sections" />
            Create section
          </h2>
          <form className="studio-form" onSubmit={handleCreate}>
            <label className="form-field">
              <span className="desk-line">
                <LineMark name="sections" size={14} />
                Short name
              </span>
              <input
                required
                placeholder="A"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label className="form-field">
              <span className="desk-line">
                <LineMark name="year" size={14} />
                School year
              </span>
              <select value={form.school_year} onChange={(event) => setForm({ ...form, school_year: event.target.value })}>
                {years.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span className="desk-line">
                <LineMark name="classes" size={14} />
                Grade
              </span>
              <select
                value={form.grade_level}
                onChange={(event) => {
                  const grade = event.target.value;
                  const nextPrograms = programs.filter((row) => row.grade_level === grade);
                  setForm({ ...form, grade_level: grade, program: nextPrograms[0] ? String(nextPrograms[0].id) : '' });
                }}
              >
                <option>Grade 11</option>
                <option>Grade 12</option>
              </select>
            </label>
            <label className="form-field">
              <span className="desk-line">
                <LineMark name="sections" size={14} />
                Program
              </span>
              <select value={form.program} onChange={(event) => setForm({ ...form, program: event.target.value })}>
                {gradePrograms.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.code} · {row.name}
                  </option>
                ))}
              </select>
            </label>
            <p className="studio-empty is-wide">Shows as {preview}</p>
            <div className="studio-form-actions">
              <button className="btn" type="submit" disabled={Boolean(busy)}>
                {busy === 'create' ? 'Saving…' : 'Create section'}
              </button>
            </div>
          </form>
        </section>

        <section className="card studio-panel">
          <h2>
            <LineMark name="sections" />
            Opened sections
          </h2>
          {sections.length === 0 ? <p className="studio-empty">No sections yet.</p> : null}
          {Object.entries(grouped).map(([key, rows]) => (
            <div className="studio-group" key={key}>
              <h3>{key}</h3>
              <div className="studio-cards">
                {rows.map((row) => (
                  <article className={`card studio-card${String(row.id) === String(selectedId) ? ' is-selected' : ''}`} key={row.id}>
                    <button className="studio-expand" type="button" onClick={() => openRoster(row)}>
                      <div>
                        <p className="studio-kicker">{row.school_year_label}</p>
                        <h2>
                          <DeskMark name="sections" size={16} />
                          {sectionLabel(row)}
                        </h2>
                        <p className="studio-empty">{row.student_count || 0} students</p>
                      </div>
                      <span className="studio-chip studio-chip-soft">Roster</span>
                    </button>
                    <div className="studio-actions">
                      <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => archive(row)}>
                        {busy === `archive-${row.id}` ? 'Archiving…' : 'Archive'}
                      </button>
                      {row.can_delete ? (
                        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => remove(row)}>
                          {busy === `delete-${row.id}` ? 'Deleting…' : 'Delete'}
                        </button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>

      {selected ? (
        <section className="card studio-panel">
          <div className="studio-toolbar">
            <div>
              <p className="studio-kicker">Selected section</p>
              <h2>
                <LineMark name="sections" />
                {sectionLabel(selected)}
              </h2>
            </div>
            <label className="studio-search">
              <span className="desk-line">
                <LineMark name="sections" size={14} />
                Short name
              </span>
              <input value={editName} onChange={(event) => setEditName(event.target.value)} />
            </label>
            <button className="btn" type="button" disabled={Boolean(busy)} onClick={saveName}>
              {busy === 'rename' ? 'Saving…' : 'Save name'}
            </button>
          </div>
          {roster.length === 0 ? (
            <p className="studio-empty">{busy.startsWith('roster') ? 'Loading roster…' : 'No students placed here yet.'}</p>
          ) : (
            <div className="studio-table-wrap">
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>LRN</th>
                    <th>Contact</th>
                  </tr>
                </thead>
                <tbody>
                  {roster.map((row) => (
                    <tr key={row.student_id}>
                      <td>
                        <span className="desk-line">
                          <LineMark name="user" size={14} />
                          {row.name}
                        </span>
                      </td>
                      <td>{row.lrn}</td>
                      <td>{row.contact_number || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
