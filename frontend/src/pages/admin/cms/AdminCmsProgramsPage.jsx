import { useEffect, useMemo, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import {
  createAdminProgram,
  createAdminSubject,
  fetchAdminPrograms,
  saveAdminProgram,
} from '../../../services/cmsService';
import './AdminCms.css';

const KINDS = [
  ['core', 'Core'],
  ['elective', 'Elective'],
  ['applied', 'Applied'],
  ['specialized', 'Specialized'],
];

function emptyForm() {
  return {
    code: '',
    name: '',
    summary: '',
    description: '',
    track: '',
    grade_level: 'Grade 11',
    pathwaysText: '',
    is_active: true,
    sort_order: 0,
    subjects: [],
  };
}

function formFromProgram(program) {
  return {
    code: program.code || '',
    name: program.name || '',
    summary: program.summary || '',
    description: program.description || '',
    track: program.track || '',
    grade_level: program.grade_level || 'Grade 11',
    pathwaysText: (program.pathways || []).join('\n'),
    is_active: program.is_active !== false,
    sort_order: program.sort_order ?? 0,
    subjects: (program.subjects || []).map((row) => ({
      subject_id: String(row.id),
      kind: row.kind || 'core',
      term: row.term ?? '',
    })),
  };
}

function payloadFromForm(form, includeCode) {
  const payload = {
    name: form.name.trim(),
    summary: form.summary,
    description: form.description,
    track: form.track.trim(),
    grade_level: form.grade_level,
    pathways: form.pathwaysText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean),
    is_active: form.is_active,
    sort_order: Number(form.sort_order) || 0,
    subjects: form.subjects
      .filter((row) => row.subject_id)
      .map((row) => ({
        subject_id: Number(row.subject_id),
        kind: row.kind,
        term: row.term === '' ? null : Number(row.term),
      })),
  };
  if (includeCode) payload.code = form.code.trim();
  return payload;
}

export default function AdminCmsProgramsPage() {
  const [programs, setPrograms] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [newSubject, setNewSubject] = useState({ code: '', name: '' });
  const [addSubjectId, setAddSubjectId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load(keepId) {
    const data = await fetchAdminPrograms();
    const rows = data.programs || [];
    setPrograms(rows);
    setSubjects(data.subjects || []);
    return rows.find((row) => String(row.id) === String(keepId)) || rows[0] || null;
  }

  useEffect(() => {
    load()
      .then((first) => {
        if (!first) return;
        setSelectedId(first.id);
        setForm(formFromProgram(first));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const unusedSubjects = useMemo(() => {
    const used = new Set(form.subjects.map((row) => String(row.subject_id)));
    return subjects.filter((row) => !used.has(String(row.id)));
  }, [form.subjects, subjects]);

  function selectProgram(program) {
    setCreating(false);
    setSelectedId(program.id);
    setForm(formFromProgram(program));
    setAddSubjectId('');
    setMessage('');
    setError('');
  }

  function startCreate() {
    setCreating(true);
    setSelectedId(null);
    setForm(emptyForm());
    setAddSubjectId('');
    setMessage('');
    setError('');
  }

  function setSubjectRow(index, patch) {
    setForm((current) => ({
      ...current,
      subjects: current.subjects.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)),
    }));
  }

  function removeSubject(index) {
    setForm((current) => ({
      ...current,
      subjects: current.subjects.filter((_, rowIndex) => rowIndex !== index),
    }));
  }

  function addSubject() {
    if (!addSubjectId) return;
    setForm((current) => ({
      ...current,
      subjects: [...current.subjects, { subject_id: addSubjectId, kind: 'core', term: '' }],
    }));
    setAddSubjectId('');
  }

  async function handleSave(event) {
    event.preventDefault();
    setError('');
    try {
      const saved = creating
        ? await createAdminProgram(payloadFromForm(form, true))
        : await saveAdminProgram(selectedId, payloadFromForm(form, false));
      const next = await load(saved.id);
      setCreating(false);
      if (next) {
        setSelectedId(next.id);
        setForm(formFromProgram(next));
      }
      setMessage(creating ? 'Program added.' : 'Program saved.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateSubject(event) {
    event.preventDefault();
    setError('');
    try {
      const created = await createAdminSubject(newSubject);
      setSubjects((rows) => [...rows, created].sort((a, b) => a.name.localeCompare(b.name)));
      setForm((current) => ({
        ...current,
        subjects: [...current.subjects, { subject_id: String(created.id), kind: 'core', term: '' }],
      }));
      setNewSubject({ code: '', name: '' });
      setMessage('Subject added to the catalog.');
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading label="Loading programs…" />;

  return (
    <div className="cms-programs">
      <aside className="cms-rail">
        {programs.map((program) => (
          <button
            key={program.id}
            type="button"
            className={program.id === selectedId && !creating ? 'is-active' : ''}
            onClick={() => selectProgram(program)}
          >
            {program.code}
            <em>{program.is_active ? program.grade_level : 'Hidden'}</em>
          </button>
        ))}
        <button type="button" className={creating ? 'is-active' : ''} onClick={startCreate}>
          New program
        </button>
      </aside>

      <div>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <form className="card cms-card" onSubmit={handleSave}>
        <h2 className="desk-line">
          <LineMark name="sections" />
          {creating ? 'Add program' : form.code || 'Program'}
        </h2>
        {creating ? (
          <label className="form-field">
            <FieldLabel>Code</FieldLabel>
            <input
              value={form.code}
              onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })}
              placeholder="ASH"
              required
            />
          </label>
        ) : null}
        <label className="form-field">
          <FieldLabel>Name</FieldLabel>
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
        </label>
        <div className="admin-cms-inline">
          <label className="form-field">
            <FieldLabel>Grade</FieldLabel>
            <select value={form.grade_level} onChange={(event) => setForm({ ...form, grade_level: event.target.value })}>
              <option value="Grade 11">Grade 11</option>
              <option value="Grade 12">Grade 12</option>
            </select>
          </label>
          <label className="form-field">
            <FieldLabel>Track</FieldLabel>
            <input value={form.track} onChange={(event) => setForm({ ...form, track: event.target.value })} />
          </label>
          <label className="form-field">
            <FieldLabel>Sort</FieldLabel>
            <input
              type="number"
              min="0"
              value={form.sort_order}
              onChange={(event) => setForm({ ...form, sort_order: event.target.value })}
            />
          </label>
        </div>
        <div className="cms-grid-2">
        <label className="form-field">
          <FieldLabel>Summary</FieldLabel>
          <textarea rows={3} value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} />
        </label>
        <label className="form-field">
          <FieldLabel>Description</FieldLabel>
          <textarea
            rows={4}
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
          />
        </label>
        </div>
        <label className="form-field">
          <FieldLabel>Pathways (one per line)</FieldLabel>
          <textarea
            rows={3}
            value={form.pathwaysText}
            onChange={(event) => setForm({ ...form, pathwaysText: event.target.value })}
          />
        </label>
        <label className="form-field admin-cms-check">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
          />
          Show on the public Programs page
        </label>

        <h3 className="desk-line">
          <LineMark name="classes" />
          Curriculum subjects
        </h3>
        <div className="admin-school-table-wrap">
          <table className="admin-school-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Kind</th>
                <th>Term</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {form.subjects.length ? (
                form.subjects.map((row, index) => {
                  const subject = subjects.find((item) => String(item.id) === String(row.subject_id));
                  return (
                    <tr key={`${row.subject_id}-${index}`}>
                      <td>{subject ? subject.name : 'Unknown subject'}</td>
                      <td>
                        <select value={row.kind} onChange={(event) => setSubjectRow(index, { kind: event.target.value })}>
                          {KINDS.map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select value={row.term} onChange={(event) => setSubjectRow(index, { term: event.target.value })}>
                          <option value="">Any</option>
                          <option value="1">1</option>
                          <option value="2">2</option>
                          <option value="3">3</option>
                        </select>
                      </td>
                      <td>
                        <button className="btn btn-secondary" type="button" onClick={() => removeSubject(index)}>
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4}>No subjects yet. Add from the catalog below.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="admin-cms-inline">
          <label className="form-field">
            <FieldLabel>Add existing subject</FieldLabel>
            <select value={addSubjectId} onChange={(event) => setAddSubjectId(event.target.value)}>
              <option value="">Choose a subject</option>
              {unusedSubjects.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-secondary" type="button" onClick={addSubject} disabled={!addSubjectId}>
            Add subject
          </button>
        </div>
        <div className="cms-save">
          <button className="btn" type="submit">
            {creating ? 'Create program' : 'Save program'}
          </button>
        </div>
      </form>

      <form className="card cms-card" onSubmit={handleCreateSubject}>
        <h2 className="desk-line">
          <LineMark name="classes" />
          New subject
        </h2>
        <p className="admin-meta">Adds a catalog subject you can attach to any program.</p>
        <div className="admin-cms-inline">
          <label className="form-field">
            <FieldLabel>Code</FieldLabel>
            <input
              value={newSubject.code}
              onChange={(event) => setNewSubject({ ...newSubject, code: event.target.value })}
              placeholder="eff-comm"
              required
            />
          </label>
          <label className="form-field">
            <FieldLabel>Name</FieldLabel>
            <input
              value={newSubject.name}
              onChange={(event) => setNewSubject({ ...newSubject, name: event.target.value })}
              required
            />
          </label>
          <button className="btn btn-secondary" type="submit">
            Add to catalog
          </button>
        </div>
      </form>
      </div>
    </div>
  );
}
