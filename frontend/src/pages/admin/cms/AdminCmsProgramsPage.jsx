import { useEffect, useMemo, useState } from 'react';
import { useProposal } from '../../../components/Access/proposalContext';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
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

const TERMS = [1, 2, 3];

function emptyForm() {
  return {
    code: '',
    name: '',
    summary: '',
    description: '',
    track: '',
    grade_level: 'Grade 11',
    curriculum: '',
    continues_to: '',
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
    curriculum: program.curriculum || '',
    continues_to: program.continues_to ? String(program.continues_to) : '',
    pathwaysText: (program.pathways || []).join('\n'),
    is_active: program.is_active !== false,
    sort_order: program.sort_order ?? 0,
    subjects: (program.subjects || []).map((row) => ({
      subject_id: String(row.id),
      kind: row.kind || 'core',
      terms: row.terms || [],
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
    curriculum: form.curriculum || null,
    continues_to: form.grade_level === 'Grade 11' && form.continues_to ? Number(form.continues_to) : null,
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
        terms: row.terms,
      })),
  };
  if (includeCode) payload.code = form.code.trim();
  return payload;
}

// What a Head Teacher tagged to edit programs may propose (the server accepts the same fields).
const PROPOSABLE = ['summary', 'description', 'track', 'pathways', 'subjects'];

function changedFields(before, after) {
  return Object.fromEntries(
    PROPOSABLE.filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key])).map((key) => [
      key,
      after[key],
    ]),
  );
}

export default function AdminCmsProgramsPage() {
  const confirm = useConfirm();
  const proposal = useProposal();
  const [programs, setPrograms] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [curricula, setCurricula] = useState([]);
  const [domains, setDomains] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [newSubject, setNewSubject] = useState({ code: '', name: '', skill_domain: '' });
  const [addSubjectId, setAddSubjectId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load(keepId) {
    const data = await fetchAdminPrograms();
    const rows = data.programs || [];
    setPrograms(rows);
    setSubjects(data.subjects || []);
    setCurricula(data.curricula || []);
    setDomains(data.skill_domains || []);
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

  const grade12Programs = useMemo(() => programs.filter((row) => row.grade_level === 'Grade 12'), [programs]);
  const domainLabel = (key) => domains.find((row) => row.key === key)?.label || '';

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

  // No term ticked means the subject runs every term.
  function toggleTerm(index, number) {
    const terms = form.subjects[index].terms;
    const next = terms.includes(number) ? terms.filter((value) => value !== number) : [...terms, number].sort();
    setSubjectRow(index, { terms: next });
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
      subjects: [...current.subjects, { subject_id: addSubjectId, kind: 'core', terms: [] }],
    }));
    setAddSubjectId('');
  }

  async function proposeChanges() {
    const original = programs.find((row) => row.id === selectedId);
    const changes = changedFields(payloadFromForm(formFromProgram(original), false), payloadFromForm(form, false));
    if (!Object.keys(changes).length) {
      setError('Nothing has changed yet.');
      return;
    }
    setError('');
    try {
      const sent = await proposal.propose(
        { program: selectedId, changes },
        {
          title: `Propose changes to ${form.code}?`,
          facts: [{ label: 'Changes', value: Object.keys(changes).join(', ') }],
        },
      );
      if (sent) setMessage('Sent to the Admin for approval. Follow it under My access.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSave(event) {
    event.preventDefault();
    if (proposal) return proposeChanges();
    const answer = await confirm({
      title: creating ? `Add program ${form.code}?` : `Save changes to ${form.code}?`,
      body: 'The Programs page and the program choices on the Register page update as soon as you confirm.',
      confirmLabel: creating ? 'Add program' : 'Save program',
    });
    if (!answer) return;
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
        subjects: [...current.subjects, { subject_id: String(created.id), kind: 'core', terms: [] }],
      }));
      setNewSubject({ code: '', name: '', skill_domain: '' });
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
        {proposal ? null : (
          <button type="button" className={creating ? 'is-active' : ''} onClick={startCreate}>
            New program
          </button>
        )}
      </aside>

      <div>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <form className="card cms-card" onSubmit={handleSave}>
          <h2 className="desk-line">
            <LineMark name="sections" />
            {creating ? 'Add program' : form.code || 'Program'}
          </h2>
          {proposal ? (
            <p className="admin-meta">
              You can propose changes to the summary, description, track, pathways and subjects.
            </p>
          ) : null}
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
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
              disabled={Boolean(proposal)}
            />
          </label>
          <div className="admin-cms-inline">
            <label className="form-field">
              <FieldLabel>Grade</FieldLabel>
              <select
                value={form.grade_level}
                onChange={(event) => setForm({ ...form, grade_level: event.target.value })}
                disabled={Boolean(proposal)}
              >
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
                disabled={Boolean(proposal)}
              />
            </label>
          </div>
          <div className="admin-cms-inline">
            <label className="form-field">
              <FieldLabel>Curriculum</FieldLabel>
              <select
                value={form.curriculum}
                onChange={(event) => setForm({ ...form, curriculum: event.target.value })}
                disabled={Boolean(proposal)}
              >
                <option value="">Not set</option>
                {curricula.map((row) => (
                  <option key={row.code} value={row.code}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            {form.grade_level === 'Grade 11' ? (
              <label className="form-field">
                <FieldLabel>Leads to (Grade 12)</FieldLabel>
                <select
                  value={form.continues_to}
                  onChange={(event) => setForm({ ...form, continues_to: event.target.value })}
                  disabled={Boolean(proposal)}
                >
                  <option value="">Not set</option>
                  {grade12Programs.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.code} — {row.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          <div className="cms-grid-2">
            <label className="form-field">
              <FieldLabel>Summary</FieldLabel>
              <textarea
                rows={3}
                value={form.summary}
                onChange={(event) => setForm({ ...form, summary: event.target.value })}
              />
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
              disabled={Boolean(proposal)}
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
                  <th title="Each new school year starts from these. The Head Teacher sets the terms for the year itself.">
                    Default terms
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.subjects.length ? (
                  form.subjects.map((row, index) => {
                    const subject = subjects.find((item) => String(item.id) === String(row.subject_id));
                    return (
                      <tr key={`${row.subject_id}-${index}`}>
                        <td>
                          {subject ? subject.name : 'Unknown subject'}
                          {subject && !subject.skill_domain ? (
                            <span className="admin-meta"> · No skill domain (not used for college matching)</span>
                          ) : null}
                          {subject?.skill_domain ? (
                            <span className="admin-meta"> · {domainLabel(subject.skill_domain)}</span>
                          ) : null}
                        </td>
                        <td>
                          <select
                            value={row.kind}
                            onChange={(event) => setSubjectRow(index, { kind: event.target.value })}
                          >
                            {KINDS.map(([value, label]) => (
                              <option key={value} value={value}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <div className="admin-cms-terms" role="group" aria-label="Default terms">
                            {TERMS.map((number) => (
                              <label key={number} className={row.terms.includes(number) ? 'is-on' : ''}>
                                <input
                                  type="checkbox"
                                  checked={row.terms.includes(number)}
                                  onChange={() => toggleTerm(index, number)}
                                />
                                T{number}
                              </label>
                            ))}
                            {row.terms.length ? null : <small>All terms</small>}
                          </div>
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
              {proposal ? 'Submit for approval' : creating ? 'Create program' : 'Save program'}
            </button>
          </div>
        </form>

        {proposal ? null : (
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
              <label className="form-field">
                <FieldLabel>Skill domain</FieldLabel>
                <select
                  value={newSubject.skill_domain}
                  onChange={(event) => setNewSubject({ ...newSubject, skill_domain: event.target.value })}
                >
                  <option value="">None (not used for college matching)</option>
                  {domains.map((row) => (
                    <option key={row.key} value={row.key}>
                      {row.label}
                    </option>
                  ))}
                </select>
              </label>
              <button className="btn btn-secondary" type="submit">
                Add to catalog
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
