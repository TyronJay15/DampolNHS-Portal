import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  activateSection,
  archiveSection,
  deleteAssignment,
  fetchAssignments,
  fetchPlacements,
  fetchSectionDetail,
  fetchTeachers,
  saveAssignment,
  savePlacement,
  savePlacementsBulk,
  saveSection,
} from '../../services/adminService';
import { isCapacityError, programChangeNote } from '../../utils/placement';
import { sectionLabel } from '../../utils/sectionLabel';
import { genderLabel } from '../../utils/gender';

const STEPS = [
  { id: 'section', label: 'Section' },
  { id: 'students', label: 'Students' },
  { id: 'adviser', label: 'Adviser' },
  { id: 'teachers', label: 'Teachers' },
  { id: 'review', label: 'Review' },
];

export default function HeadSectionWorkspacePage() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const step = searchParams.get('step') || 'section';

  const confirm = useConfirm();
  const [detail, setDetail] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [selected, setSelected] = useState({});
  const [studentQuery, setStudentQuery] = useState('');
  const [adviserId, setAdviserId] = useState('');
  const [teacherPick, setTeacherPick] = useState({ subject: '', teacher: '' });
  const [capacity, setCapacity] = useState('40');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function reload() {
    const [sectionData, placementRows, teacherRows] = await Promise.all([
      fetchSectionDetail(sectionId),
      fetchPlacements(),
      fetchTeachers(),
    ]);
    setDetail(sectionData);
    setStudents(placementRows);
    setTeachers(teacherRows);
    setCapacity(String(sectionData.capacity || 40));
    if (sectionData.progress?.adviser_id) setAdviserId(String(sectionData.progress.adviser_id));
    return sectionData;
  }

  useEffect(() => {
    reload()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sectionId]);

  const section = detail;
  const progress = detail?.progress;
  const identityLocked = detail?.identity_locked;
  const isActive = section?.status === 'active';

  // Unplaced students must match the program; placed students from any program can transfer in.
  const candidates = useMemo(() => {
    if (!section) return [];
    const needle = studentQuery.trim().toLowerCase();
    return students.filter((row) => {
      if (row.section_id === section.id) return false;
      if (row.grade_level && section.grade_level && row.grade_level !== section.grade_level) return false;
      if (!row.placed && row.program_code && section.program_code && row.program_code !== section.program_code) return false;
      if (!needle) return true;
      return [row.name, row.lrn, row.program_code].join(' ').toLowerCase().includes(needle);
    });
  }, [students, section, studentQuery]);

  const roster = useMemo(
    () => students.filter((row) => row.section_id === Number(sectionId)),
    [students, sectionId],
  );

  const chosen = candidates.filter((row) => !row.placed && selected[row.student_id]);

  function goStep(next) {
    setSearchParams({ step: next });
    setError('');
    setMessage('');
  }

  async function saveCapacity() {
    setBusy('capacity');
    setError('');
    try {
      await saveSection(sectionId, { capacity: Number(capacity) || 40 });
      await reload();
      setMessage('Capacity updated.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  const reasonNote = { label: 'Reason', placeholder: 'Why is this change being made?' };

  // Asked again when the server reports the section is full; returns the reason, or null if declined.
  async function confirmOverCapacity(body, reason) {
    const answer = await confirm({
      title: 'Section is over capacity',
      body,
      confirmLabel: 'Proceed anyway',
      tone: 'warning',
      note: { label: 'Reason', placeholder: 'Why exceed capacity?', required: true, initial: reason },
    });
    return answer ? answer.note : null;
  }

  async function assignStudents() {
    if (chosen.length === 0) return;
    const answer = await confirm({
      title: `Assign ${chosen.length} student${chosen.length === 1 ? '' : 's'}?`,
      body: `They are placed in ${sectionLabel(section)} and appear on its roster.`,
      confirmLabel: 'Assign students',
      facts: [
        { label: 'Selected', value: chosen.length },
        { label: 'On roster now', value: roster.length },
      ],
      note: reasonNote,
    });
    if (!answer) return;
    let reason = answer.note;
    let force = false;
    for (;;) {
      setBusy('students');
      setError('');
      try {
        const result = await savePlacementsBulk({
          section: Number(sectionId),
          students: chosen.map((row) => row.student_id),
          override_capacity: force,
          reason,
        });
        setSelected({});
        await reload();
        const failedNote = result.failed?.length ? ` ${result.failed.length} could not be placed.` : '';
        setMessage(`Placed ${result.placed} student(s).${failedNote}`);
        return;
      } catch (err) {
        if (force || !isCapacityError(err)) {
          setError(err.message);
          return;
        }
        setBusy('');
        reason = await confirmOverCapacity('These students exceed the section capacity. Proceed anyway?', reason);
        if (reason === null) return;
        force = true;
      } finally {
        setBusy('');
      }
    }
  }

  async function transferStudent(row) {
    const note = programChangeNote(row, section);
    const answer = await confirm({
      title: `Transfer ${row.name}?`,
      body: `Move from ${row.section} to ${sectionLabel(section)}.`,
      confirmLabel: 'Transfer',
      warning: note || undefined,
      note: reasonNote,
    });
    if (!answer) return;
    let reason = answer.note;
    let force = false;
    for (;;) {
      setBusy(`move-${row.student_id}`);
      setError('');
      try {
        await savePlacement({
          student: row.student_id,
          section: Number(sectionId),
          transfer: true,
          override_capacity: force,
          reason,
        });
        await reload();
        setMessage(`Transferred ${row.name}.`);
        return;
      } catch (err) {
        if (force || !isCapacityError(err)) {
          setError(err.message);
          return;
        }
        setBusy('');
        reason = await confirmOverCapacity(`Moving ${row.name} exceeds the section capacity. Proceed anyway?`, reason);
        if (reason === null) return;
        force = true;
      } finally {
        setBusy('');
      }
    }
  }

  async function assignAdviser() {
    if (!adviserId) return;
    const teacher = teachers.find((row) => String(row.id) === adviserId);
    const answer = await confirm({
      title: `Assign ${teacher?.name} as adviser?`,
      body: `They become the adviser of ${sectionLabel(section)}.`,
      confirmLabel: 'Assign adviser',
      note: reasonNote,
    });
    if (!answer) return;
    setBusy('adviser');
    setError('');
    try {
      await saveAssignment({
        section: Number(sectionId),
        teacher: Number(adviserId),
        type: 'adviser',
        reason: answer.note,
      });
      await reload();
      setMessage('Adviser assigned.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function assignSubject() {
    if (!teacherPick.subject || !teacherPick.teacher) return;
    const subjectRow = progress?.subject_rows?.find((row) => String(row.subject_id) === String(teacherPick.subject));
    const teacher = teachers.find((row) => String(row.id) === teacherPick.teacher);
    const answer = await confirm({
      title: `Assign ${teacher?.name} to ${subjectRow?.subject}?`,
      body: `They teach this subject in ${sectionLabel(section)}.`,
      confirmLabel: 'Assign teacher',
      note: reasonNote,
    });
    if (!answer) return;
    setBusy('subject');
    setError('');
    try {
      await saveAssignment({
        section: Number(sectionId),
        teacher: Number(teacherPick.teacher),
        subject: Number(teacherPick.subject),
        type: 'subject_teacher',
        reason: answer.note,
      });
      setTeacherPick({ subject: '', teacher: '' });
      await reload();
      setMessage('Subject teacher assigned.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function removeSubject(row) {
    if (!row.teacher_id) return;
    setBusy(`end-${row.subject_id}`);
    setError('');
    try {
      const assignments = await fetchAssignments();
      const active = assignments.find(
        (item) =>
          item.section_id === Number(sectionId) &&
          item.subject_id === row.subject_id &&
          item.type === 'subject_teacher',
      );
      if (active) await deleteAssignment(active.id);
      await reload();
      setMessage(`Removed teacher from ${row.subject}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function activate(force = false) {
    const blocked = detail?.activation?.blocked || [];
    const answer = await confirm(
      force
        ? {
            title: 'Activate with incomplete setup?',
            body: `${sectionLabel(section)} goes live now. Teachers can be assigned and grading can start; finish the checklist later.`,
            confirmLabel: 'Activate anyway',
            tone: 'warning',
            warning: blocked.length ? blocked : undefined,
            note: { ...reasonNote, required: true },
          }
        : {
            title: `Activate ${sectionLabel(section)}?`,
            body: 'The section goes live. Its identity is locked and teachers can start grading.',
            confirmLabel: 'Activate section',
          },
    );
    if (!answer) return;
    setBusy('activate');
    setError('');
    try {
      await activateSection(sectionId, {
        allow_incomplete: force,
        reason: force ? answer.note : '',
      });
      await reload();
      setMessage(force ? 'Section activated with incomplete setup. You can finish assignments later.' : 'Section is now active.');
      goStep('review');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function archive() {
    const answer = await confirm({
      title: `Archive ${sectionLabel(section)}?`,
      body: 'The section leaves live use. History and grades are preserved and you can restore it from the Archive.',
      confirmLabel: 'Archive section',
      tone: 'warning',
    });
    if (!answer) return;
    setBusy('archive');
    setError('');
    try {
      await archiveSection(sectionId);
      navigate('/head/archive');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading section workspace…" />;
  if (!section) return <p className="alert alert-error">Section not found.</p>;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Section workspace" title={sectionLabel(section)} icon="sections">
        <p>
          {isActive
            ? 'ACTIVE — controlled changes allowed. Section identity is locked; assignments can be updated with confirmation.'
            : 'Complete each step, then activate when ready.'}
        </p>
        <div className="studio-hero-meta">
          <span className={`studio-chip ${isActive ? 'is-approved' : ''}`}>{section.status?.replace('_', ' ')}</span>
          <span className="studio-chip">{progress?.progress_percent || 0}% complete</span>
        </div>
      </PageHead>

      <div className="studio-actions studio-toolbar-actions">
        <Link to="/head/sections">Back to section management</Link>
        {!section.archived ? (
          <button className="btn btn-secondary" type="button" disabled={busy === 'archive'} onClick={archive}>
            Archive section
          </button>
        ) : null}
      </div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-wizard-steps">
        {STEPS.map((item, index) => (
          <button
            key={item.id}
            type="button"
            className={`studio-wizard-step${step === item.id ? ' is-active' : ''}${
              progress?.checklist?.[index]?.done ? ' is-done' : ''
            }`}
            onClick={() => goStep(item.id)}
          >
            <span>{index + 1}</span>
            {item.label}
          </button>
        ))}
      </div>

      {step === 'section' ? (
        <section className="card studio-panel">
          <h2>Section information {identityLocked ? '— locked' : ''}</h2>
          <div className="studio-lock-grid">
            <div><strong>School year</strong><p>{section.school_year_label}</p></div>
            <div><strong>Grade level</strong><p>{section.grade_level}</p></div>
            <div><strong>Program</strong><p>{section.program_code} · {section.program_name}</p></div>
            <div><strong>Section name</strong><p>{section.name}</p></div>
          </div>
          <label className="form-field">
            <span>Capacity</span>
            <input value={capacity} onChange={(event) => setCapacity(event.target.value)} />
          </label>
          <button className="btn btn-secondary" type="button" disabled={busy === 'capacity'} onClick={saveCapacity}>
            {busy === 'capacity' ? 'Saving…' : 'Save capacity'}
          </button>
        </section>
      ) : null}

      {step === 'students' ? (
        <section className="card studio-panel studio-table-wrap">
          <h2>Assign students ({roster.length}{section.capacity ? ` / ${section.capacity}` : ''})</h2>
          <label className="studio-search">
            <span>Search available students</span>
            <input value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} placeholder="Name or LRN" />
          </label>
          <div className="studio-table-actions studio-actions">
            <button className="btn" type="button" disabled={!chosen.length || Boolean(busy)} onClick={assignStudents}>
              Assign selected ({chosen.length})
            </button>
          </div>
          <table className="studio-table">
            <thead>
              <tr>
                <th />
                <th>Student</th>
                <th>LRN</th>
                <th>Program</th>
                <th>Current section</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((row) => (
                <tr key={row.student_id}>
                  <td>
                    {row.placed ? null : (
                      <input
                        type="checkbox"
                        checked={Boolean(selected[row.student_id])}
                        onChange={(event) =>
                          setSelected((current) => ({ ...current, [row.student_id]: event.target.checked }))
                        }
                      />
                    )}
                  </td>
                  <td>
                    {row.name}
                    {row.gender ? <p className="studio-table-sub">{genderLabel(row.gender)}</p> : null}
                  </td>
                  <td>{row.lrn}</td>
                  <td>{row.program_code || '—'}</td>
                  <td>
                    {row.placed ? (
                      <button
                        className="btn btn-secondary"
                        type="button"
                        disabled={Boolean(busy)}
                        onClick={() => transferStudent(row)}
                      >
                        Transfer from {row.section}
                      </button>
                    ) : (
                      'Available'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {roster.length ? (
            <>
              <h3>Currently in this section</h3>
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>LRN</th>
                  </tr>
                </thead>
                <tbody>
                  {roster.map((row) => (
                    <tr key={row.student_id}>
                      <td>
                        {row.name}
                        {row.gender ? <p className="studio-table-sub">{genderLabel(row.gender)}</p> : null}
                      </td>
                      <td>{row.lrn}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </section>
      ) : null}

      {step === 'adviser' ? (
        <section className="card studio-panel">
          <h2>Adviser</h2>
          <p className="studio-empty">Current: {progress?.adviser || 'None assigned'}</p>
          <label className="form-field">
            <span>Select adviser</span>
            <select value={adviserId} onChange={(event) => setAdviserId(event.target.value)}>
              <option value="">Choose teacher</option>
              {teachers.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="button" disabled={!adviserId || Boolean(busy)} onClick={assignAdviser}>
            {progress?.adviser ? 'Change adviser' : 'Assign adviser'}
          </button>
        </section>
      ) : null}

      {step === 'teachers' ? (
        <section className="card studio-panel studio-table-wrap">
          <h2>Subject teachers</h2>
          <table className="studio-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Teacher</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {(progress?.subject_rows || []).map((row) => (
                <tr key={row.subject_id}>
                  <td>{row.subject}</td>
                  <td>{row.teacher || '—'}</td>
                  <td>{row.assigned ? 'Assigned' : 'Missing'}</td>
                  <td>
                    {row.assigned && !isActive ? (
                      <button className="btn btn-secondary" type="button" onClick={() => removeSubject(row)}>
                        Remove
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="studio-form">
            <label className="form-field">
              <span>Subject</span>
              <select
                value={teacherPick.subject}
                onChange={(event) => setTeacherPick({ ...teacherPick, subject: event.target.value })}
              >
                <option value="">Choose subject</option>
                {(progress?.subject_rows || []).map((row) => (
                  <option key={row.subject_id} value={row.subject_id}>
                    {row.subject}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Teacher</span>
              <select
                value={teacherPick.teacher}
                onChange={(event) => setTeacherPick({ ...teacherPick, teacher: event.target.value })}
              >
                <option value="">Choose teacher</option>
                {teachers.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button className="btn" type="button" disabled={!teacherPick.subject || !teacherPick.teacher} onClick={assignSubject}>
            Assign teacher
          </button>
        </section>
      ) : null}

      {step === 'review' ? (
        <section className="card studio-panel">
          <h2>Review & activate</h2>
          <ul className="studio-checklist">
            {(progress?.checklist || []).map((item) => (
              <li key={item.key} className={item.done ? 'is-done' : 'is-pending'}>
                <LineMark name={item.done ? 'approve' : 'corrections'} size={14} />
                <div>
                  <strong>{item.label}</strong>
                  <p>{item.detail}</p>
                </div>
              </li>
            ))}
          </ul>
          {(detail?.activation?.blocked || []).length ? (
            <div className="alert alert-error">
              <strong>Cannot activate yet</strong>
              <ul>
                {detail.activation.blocked.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="studio-actions">
            {!isActive ? (
              <>
                <button
                  className="btn"
                  type="button"
                  disabled={!detail?.activation?.can_activate || busy === 'activate'}
                  onClick={() => activate(false)}
                >
                  {busy === 'activate' ? 'Activating…' : 'Activate section'}
                </button>
                {!detail?.activation?.can_activate ? (
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={busy === 'activate'}
                    onClick={() => activate(true)}
                  >
                    Activate anyway
                  </button>
                ) : null}
              </>
            ) : (
              <button className="btn btn-secondary" type="button" disabled={busy === 'archive'} onClick={archive}>
                Archive section
              </button>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
