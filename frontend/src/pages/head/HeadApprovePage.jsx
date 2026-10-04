import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import {
  approveAllGrades,
  approveGrades,
  approveTeacherGrades,
  fetchGradeQueues,
  fetchSchoolYears,
  returnGrades,
} from '../../services/adminService';
import { fetchTerms } from '../../services/teacherService';

export default function HeadApprovePage() {
  const { user } = useAuth();
  const confirm = useConfirm();
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [teachers, setTeachers] = useState([]);
  const [openTeachers, setOpenTeachers] = useState({});
  const [waiting, setWaiting] = useState(0);
  const [busyKey, setBusyKey] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSchoolYears()
      .then((years) => {
        const current = years.find((year) => year.is_current) || years[0];
        if (!current) return [];
        return fetchTerms(current.id);
      })
      .then((termRows) => {
        setTerms(termRows);
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
        if (!cancelled) {
          const list = data.teachers || [];
          setTeachers(list);
          setWaiting(data.waiting || 0);
          setOpenTeachers((current) => {
            if (Object.keys(current).length) return current;
            const next = {};
            list.forEach((teacher) => {
              const key = String(teacher.teacher_id || teacher.teacher);
              next[key] = teacher.submitted > 0 || teacher.missing > 0 || list.length <= 3;
            });
            return next;
          });
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [termId]);

  async function refreshQueues() {
    const data = await fetchGradeQueues(termId);
    setTeachers(data.teachers || []);
    setWaiting(data.waiting || 0);
  }

  function toggleTeacher(key) {
    setOpenTeachers((current) => ({ ...current, [key]: !current[key] }));
  }

  async function runSubject(group, sectionName) {
    const { section_id: sectionId, subject_id: subjectId } = group;
    const answer = await confirm({
      title: `Approve ${group.subject}?`,
      body: `${group.submitted} submitted grade(s) for ${sectionName} will be approved. The subject teacher is notified, and the adviser can then show the cards.`,
      confirmLabel: `Approve ${group.submitted}`,
    });
    if (!answer) return;
    const key = `subject-${sectionId}-${subjectId}`;
    setBusyKey(key);
    setMessage('');
    setError('');
    try {
      const result = await approveGrades({ term: Number(termId), section: sectionId, subject: subjectId });
      await refreshQueues();
      setMessage(`Approved ${result.approved} grade(s). Teachers are notified.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  async function runTeacher(teacher) {
    const teacherId = teacher.teacher_id;
    const answer = await confirm({
      title: `Approve all grades from ${teacher.teacher}?`,
      body: 'Every submitted grade from this teacher for the selected term will be approved. The teacher is notified.',
      confirmLabel: `Approve ${teacher.submitted}`,
      facts: [{ label: 'Submitted grades', value: teacher.submitted }],
    });
    if (!answer) return;
    setBusyKey(`teacher-${teacherId}`);
    setMessage('');
    setError('');
    try {
      const result = await approveTeacherGrades({ term: Number(termId), teacher: teacherId });
      await refreshQueues();
      setMessage(`Approved ${result.approved} grade(s) for this teacher.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  async function runAll() {
    const answer = await confirm({
      title: 'Approve all submitted grades?',
      body: 'Every submitted grade for the selected term will be approved. Teachers are notified, and advisers can then show the report cards.',
      confirmLabel: `Approve ${waiting}`,
      facts: [
        { label: 'Submitted grades', value: waiting },
        { label: 'Teachers waiting', value: teachers.filter((teacher) => teacher.submitted > 0).length },
      ],
    });
    if (!answer) return;
    setBusyKey('all');
    setMessage('');
    setError('');
    try {
      const result = await approveAllGrades(Number(termId));
      await refreshQueues();
      setMessage(`Approved ${result.approved} submitted grade(s).`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  async function runReturn(group, sectionName) {
    const answer = await confirm({
      title: `Return ${group.subject} to draft?`,
      body: `Submitted and approved grades for ${sectionName} go back to draft. The teacher is notified and must fix and submit again. Cards that are already shown are left untouched.`,
      confirmLabel: 'Return to draft',
      tone: 'warning',
      facts: [
        { label: 'Submitted', value: group.submitted },
        { label: 'Approved', value: group.approved },
      ],
    });
    if (!answer) return;
    const key = `return-${group.section_id}-${group.subject_id}`;
    setBusyKey(key);
    setMessage('');
    setError('');
    try {
      const result = await returnGrades({ term: Number(termId), section: group.section_id, subject: group.subject_id });
      await refreshQueues();
      setMessage(`Returned ${result.returned} grade(s) to draft.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  if (loading) return <Loading label="Loading submitted classes…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Review" title="Approve grades" icon="approve">
        <p>Every assigned subject is listed, including classes not yet encoded. Approve only acts on submitted scores.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{waiting} submitted waiting</span>
        </div>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-tabs">
        {terms.map((term) => (
          <button key={term.id} type="button" className={String(term.id) === termId ? 'is-active' : ''} onClick={() => setTermId(String(term.id))}>
            {term.label}
          </button>
        ))}
      </div>

      <div className="studio-actions">
        <button className="btn" type="button" disabled={!waiting || busyKey === 'all'} onClick={runAll}>
          {busyKey === 'all' ? 'Approving all…' : 'Approve all submitted'}
        </button>
      </div>

      {teachers.length === 0 ? (
        <p className="card studio-panel studio-empty">No assigned classes for this term yet.</p>
      ) : (
        <div className="studio-accordion-list">
          {teachers.map((teacher) => {
            const key = String(teacher.teacher_id || teacher.teacher);
            const open = Boolean(openTeachers[key]);
            return (
              <article className={`card studio-panel studio-accordion-card${open ? ' is-open' : ''}`} key={key}>
                <button type="button" className="studio-accordion-head" onClick={() => toggleTeacher(key)}>
                  <div>
                    <p className="studio-kicker">Teacher</p>
                    <h2>
                      <DeskMark name="assign" size={16} />
                      {teacher.teacher}
                    </h2>
                    <p className="studio-empty">
                      {teacher.submitted} submitted waiting
                      {teacher.missing ? ` · ${teacher.missing} not encoded` : ''}
                    </p>
                  </div>
                  <div className="studio-accordion-tools">
                    <button
                      className="btn"
                      type="button"
                      disabled={!teacher.submitted || busyKey === `teacher-${teacher.teacher_id}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        runTeacher(teacher);
                      }}
                    >
                      Approve all
                    </button>
                    <span className="studio-accordion-caret">{open ? '▾' : '▸'}</span>
                  </div>
                </button>
                {open ? (
                  <div className="studio-accordion-body">
                    {teacher.sections.map((section) => (
                      <div className="studio-section-block" key={`${key}-${section.section_id}`}>
                        <h3>{section.section}</h3>
                        <div className="studio-table-wrap">
                          <table className="studio-table">
                            <thead>
                              <tr>
                                <th>Subject</th>
                                <th>Status</th>
                                <th>Encoded</th>
                                <th>Submitted</th>
                                <th>Approved</th>
                                <th />
                              </tr>
                            </thead>
                            <tbody>
                              {section.subjects.map((group) => (
                                <tr key={`${group.section_id}-${group.subject_id}`}>
                                  <td>{group.subject}</td>
                                  <td>
                                    <span
                                      className={`studio-status ${
                                        group.workflow === 'submitted'
                                          ? 'is-submitted'
                                          : group.workflow === 'approved' || group.progress === 'encoded'
                                            ? 'is-encoded'
                                            : group.progress === 'in_progress'
                                              ? 'is-progress'
                                              : group.progress === 'not_encoded'
                                                ? 'is-wait'
                                                : ''
                                      }`}
                                    >
                                      {group.workflow_label || group.progress_label || 'Not encoded'}
                                    </span>
                                  </td>
                                  <td>
                                    {group.encoded}/{group.roster}
                                  </td>
                                  <td>{group.submitted}</td>
                                  <td>{group.approved}</td>
                                  <td>
                                    <div className="studio-actions">
                                      <button className="btn" type="button" disabled={!group.submitted} onClick={() => runSubject(group, section.section)}>Approve</button>
                                      <button className="btn btn-secondary" type="button" disabled={!group.submitted && !group.approved} onClick={() => runReturn(group, section.section)}>Return</button>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
