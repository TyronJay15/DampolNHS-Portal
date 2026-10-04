import { useEffect, useMemo, useState } from 'react';
import { useProposal } from '../../components/Access/proposalContext';
import AdvancedToolBanner from '../../components/AdvancedToolBanner/AdvancedToolBanner';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  deleteAssignment,
  fetchAssignments,
  fetchSections,
  fetchSubjects,
  fetchTeachers,
  saveAssignment,
} from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';

export default function HeadAssignPage() {
  const confirm = useConfirm();
  // Set when a teacher tagged to prepare assignments opens this page: new duties become requests.
  const proposal = useProposal();
  const [view, setView] = useState('section');
  const [assignments, setAssignments] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [sectionId, setSectionId] = useState('');
  const [teacherId, setTeacherId] = useState('');
  const [form, setForm] = useState({ teacher: '', subject: '', type: 'subject_teacher' });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const [assignmentRows, teacherRows, sectionRows] = await Promise.all([
      fetchAssignments(),
      fetchTeachers(),
      fetchSections(),
    ]);
    setAssignments(assignmentRows);
    setTeachers(teacherRows);
    setSections(sectionRows);
    setSectionId((current) => current || (sectionRows[0] ? String(sectionRows[0].id) : ''));
    setTeacherId((current) => current || (teacherRows[0] ? String(teacherRows[0].id) : ''));
    setForm((current) => ({
      ...current,
      teacher: current.teacher || (teacherRows[0] ? String(teacherRows[0].id) : ''),
    }));
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const section = sections.find((row) => String(row.id) === String(sectionId));
  const teacher = teachers.find((row) => String(row.id) === String(teacherId));

  useEffect(() => {
    if (!section?.program_code) {
      setSubjects([]);
      return undefined;
    }
    let cancelled = false;
    fetchSubjects(section.program_code)
      .then((rows) => {
        if (!cancelled) setSubjects(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [section?.program_code]);

  const sectionDuties = useMemo(
    () => assignments.filter((row) => String(row.section_id) === String(sectionId)),
    [assignments, sectionId],
  );
  const teacherDuties = useMemo(
    () => assignments.filter((row) => String(row.teacher_id) === String(teacherId)),
    [assignments, teacherId],
  );
  const adviser = sectionDuties.find((row) => row.type === 'adviser');
  const takenSubjects = new Set(sectionDuties.filter((row) => row.subject_id).map((row) => String(row.subject_id)));
  const openSubjects = subjects.filter((row) => !takenSubjects.has(String(row.id)));

  async function proposeDuty(payload) {
    const person = teachers.find((row) => String(row.id) === String(payload.teacher));
    const subject = subjects.find((row) => String(row.id) === String(payload.subject));
    try {
      const sent = await proposal.propose(payload, {
        title: `Propose ${person?.name || 'this teacher'} as ${payload.type === 'adviser' ? 'adviser' : subject?.name || 'subject teacher'}?`,
        facts: [{ label: 'Section', value: sectionLabel(section) }],
      });
      if (!sent) return;
      setForm((current) => ({ ...current, subject: '' }));
      setMessage('Sent to the Head Teacher for approval. Follow it under My access.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (proposal) {
      setError('');
      setMessage('');
      return proposeDuty({
        teacher: Number(view === 'teacher' ? teacherId : form.teacher),
        section: Number(sectionId),
        subject: form.type === 'adviser' ? null : Number(form.subject) || null,
        type: form.type,
      });
    }
    setBusy('create');
    setError('');
    setMessage('');
    try {
      const saved = await saveAssignment({
        teacher: Number(view === 'teacher' ? teacherId : form.teacher),
        section: Number(sectionId),
        subject: form.type === 'adviser' ? null : Number(form.subject) || null,
        type: form.type,
      });
      setMessage(
        form.type === 'adviser'
          ? `${saved.teacher} is adviser of ${saved.section}. Visible in Section Workspace.`
          : `${saved.teacher} teaches ${saved.subject} in ${saved.section}. Visible in Section Workspace.`,
      );
      setForm((current) => ({ ...current, subject: '' }));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function endDuty(row) {
    const role = row.type === 'adviser' ? 'adviser' : row.subject;
    const answer = await confirm({
      title: `End ${row.teacher}'s duty?`,
      body: `${row.teacher} will no longer be the ${role}${row.section ? ` for ${row.section}` : ''} and loses access to that class. The duty moves to the Archive, where it can be restored.`,
      confirmLabel: 'End duty',
      tone: 'warning',
    });
    if (!answer) return;
    setBusy(`del-${row.id}`);
    setError('');
    try {
      await deleteAssignment(row.id);
      setMessage(`${row.teacher} duty moved to Archive.`);
      setAssignments((rows) => rows.filter((item) => item.id !== row.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading assignments…" />;

  const duties = view === 'section' ? sectionDuties : teacherDuties;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Duties" title="Assign teachers" icon="assign">
        <p>Work by section or by teacher. Ending a duty parks it in Archive so it can be restored later.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{assignments.length} live duties</span>
        </div>
      </PageHead>
      {proposal ? null : <AdvancedToolBanner />}
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        <button type="button" className={`studio-filter${view === 'section' ? ' is-active' : ''}`} onClick={() => setView('section')}>
          By section
        </button>
        <button type="button" className={`studio-filter${view === 'teacher' ? ' is-active' : ''}`} onClick={() => setView('teacher')}>
          By teacher
        </button>
      </div>

      <div className="studio-split-panels">
        <section className="card studio-panel">
          <h2>
            <LineMark name={view === 'section' ? 'sections' : 'staff'} />
            {view === 'section' ? 'Sections' : 'Teachers'}
          </h2>
          <div className="studio-pick-list studio-pick-list-scroll">
            {view === 'section'
              ? sections.map((row) => (
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
                    <em>{row.student_count || 0} students</em>
                  </button>
                ))
              : teachers.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    className={`studio-pick${String(row.id) === String(teacherId) ? ' is-active' : ''}`}
                    onClick={() => setTeacherId(String(row.id))}
                  >
                    <strong className="desk-line">
                      <LineMark name="staff" size={14} />
                      {row.name}
                    </strong>
                    <em>{assignments.filter((item) => item.teacher_id === row.id).length} duties</em>
                  </button>
                ))}
          </div>
        </section>

        <section className="card studio-panel">
          <h2>
            <LineMark name={view === 'section' ? 'sections' : 'staff'} />
            {view === 'section'
              ? section
                ? sectionLabel(section)
                : 'Select a section'
              : teacher
                ? teacher.name
                : 'Select a teacher'}
          </h2>
          {view === 'section' && adviser ? <p className="studio-empty">Adviser · {adviser.teacher}</p> : null}

          {view === 'section' && section ? (
            <div className="studio-table-wrap">
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Teacher</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {subjects.map((subj) => {
                    const duty = sectionDuties.find((row) => String(row.subject_id) === String(subj.id));
                    return (
                      <tr key={subj.id}>
                        <td>{subj.name}</td>
                        <td>{duty ? duty.teacher : '—'}</td>
                        <td>
                          {duty && !proposal ? (
                            <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => endDuty(duty)}>End</button>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}

          <form className="studio-form" onSubmit={handleCreate}>
            {view === 'section' ? (
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="staff" size={14} />
                  Teacher
                </span>
                <select value={form.teacher} onChange={(event) => setForm({ ...form, teacher: event.target.value })}>
                  {teachers.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="form-field">
                <span className="desk-line">
                  <LineMark name="sections" size={14} />
                  Section
                </span>
                <select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
                  {sections.map((row) => (
                    <option key={row.id} value={row.id}>
                      {sectionLabel(row)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="form-field">
                <span className="desk-line">
                  <LineMark name="assign" size={14} />
                  Kind
                </span>
              <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
                <option value="subject_teacher">Subject teacher</option>
                <option value="adviser">Adviser</option>
              </select>
            </label>
            {form.type === 'adviser' ? null : (
              <label className="form-field is-wide">
                <span className="desk-line">
                  <LineMark name="classes" size={14} />
                  Open subjects
                </span>
                <select value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })}>
                  <option value="">Select subject</option>
                  {openSubjects.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.code} · {row.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <div className="studio-form-actions">
              <button className="btn" type="submit" disabled={Boolean(busy) || !sectionId || teachers.length === 0}>
                {busy === 'create' ? 'Saving…' : proposal ? 'Submit for approval' : 'Assign'}
              </button>
            </div>
          </form>

          {view === 'teacher' ? (
            duties.length === 0 ? (
              <p className="studio-empty">No live duties here yet.</p>
            ) : (
              <div className="studio-table-wrap">
                <table className="studio-table">
                  <thead>
                    <tr>
                      <th>Duty</th>
                      <th>Section</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {duties.map((row) => (
                      <tr key={row.id}>
                        <td>{row.type === 'adviser' ? 'Adviser' : row.subject}</td>
                        <td>{row.section}</td>
                        <td>
                          {proposal ? null : (
                            <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => endDuty(row)}>
                              {busy === `del-${row.id}` ? 'Ending…' : 'End duty'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : null}
        </section>
      </div>
    </div>
  );
}
