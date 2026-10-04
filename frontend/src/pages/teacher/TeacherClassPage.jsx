import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { gradeStatusIcon, progressChipClass } from '../../utils/gradeStatus';
import {
  encodeGrade,
  fetchClassGrades,
  fetchTeacherAssignments,
  fetchTerms,
  requestCorrection,
  submitClassGrades,
} from '../../services/teacherService';
import { when } from '../../utils/when';
import DutyTermTabs from './DutyTermTabs';
import { defaultTermId, dutyTerms } from './dutyTerms';

function statusClass(status) {
  if (status === 'submitted') return 'is-submitted';
  if (status === 'approved') return 'is-approved';
  if (status === 'released') return 'is-released';
  return '';
}

export default function TeacherClassPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const confirm = useConfirm();
  const [meta, setMeta] = useState(null);
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [students, setStudents] = useState([]);
  const [scores, setScores] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [correctionRow, setCorrectionRow] = useState(null);
  const [correctionScore, setCorrectionScore] = useState('');
  const [correctReason, setCorrectReason] = useState('');
  const [query, setQuery] = useState('');
  const [encodeOpen, setEncodeOpen] = useState(true);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_encode) {
          throw new Error('You cannot encode grades for that class.');
        }
        const termRows = dutyTerms(await fetchTerms(assignment.school_year_id), assignment);
        if (cancelled) return;
        setTerms(termRows);
        setTermId(defaultTermId(termRows));
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, [assignmentId]);

  useEffect(() => {
    if (!termId) return undefined;
    let cancelled = false;
    setError('');
    fetchClassGrades(assignmentId, termId)
      .then((data) => {
        if (cancelled) return;
        setMeta(data.assignment);
        setEncodeOpen(data.term?.encode_open !== false);
        setSummary(data.summary || null);
        setStudents(data.students || []);
        const next = {};
        (data.students || []).forEach((row) => {
          next[row.student_id] = row.score;
        });
        setScores(next);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [assignmentId, termId]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return students;
    return students.filter((row) => [row.name, row.lrn, row.status].join(' ').toLowerCase().includes(needle));
  }, [query, students]);

  async function saveRow(student) {
    setBusyId(student.student_id);
    setMessage('');
    setError('');
    try {
      const saved = await encodeGrade({
        assignment: Number(assignmentId),
        term: Number(termId),
        student: student.student_id,
        score: scores[student.student_id],
      });
      setStudents((rows) => rows.map((row) => (row.student_id === saved.student_id ? saved : row)));
      const data = await fetchClassGrades(assignmentId, termId);
      setSummary(data.summary || null);
      setMessage(`Saved ${saved.name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  function openCorrection(student) {
    setCorrectionRow(student);
    setCorrectionScore(scores[student.student_id] ?? student.score ?? '');
    setCorrectReason('');
  }

  function closeCorrection() {
    setCorrectionRow(null);
    setCorrectReason('');
  }

  async function sendCorrection() {
    if (!correctionRow) return;
    const student = correctionRow;
    setBusyId(student.student_id);
    setMessage('');
    setError('');
    try {
      await requestCorrection({
        assignment: Number(assignmentId),
        grade: student.grade_id,
        proposed_score: correctionScore,
        reason: correctReason,
      });
      const data = await fetchClassGrades(assignmentId, termId);
      setStudents(data.students || []);
      closeCorrection();
      setMessage(`Correction requested for ${student.name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function submitClass() {
    const drafts = students.filter((row) => row.status === 'draft').length;
    const missing = summary?.missing || 0;
    const answer = await confirm({
      title: 'Submit class grades for review?',
      body: 'Submitted grades go to the Head Teacher for approval and cannot be edited until they are returned.',
      confirmLabel: `Submit ${drafts}`,
      facts: [{ label: 'Grades to submit', value: drafts }],
      warning: missing
        ? `${missing} student${missing === 1 ? ' has' : 's have'} no score yet. Only the encoded drafts will be sent.`
        : undefined,
    });
    if (!answer) return;
    setSubmitting(true);
    setMessage('');
    setError('');
    try {
      const result = await submitClassGrades(Number(assignmentId), Number(termId));
      const data = await fetchClassGrades(assignmentId, termId);
      setStudents(data.students || []);
      setSummary(data.summary || null);
      setMessage(`Submitted ${result.submitted} draft grade(s).`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Loading label="Loading class…" />;

  const heading = meta?.section_label || meta?.section || 'Encode';

  return (
    <div className="desk studio">
      <PageHead kicker={heading} title={meta ? `${meta.subject} · ${heading}` : 'Encode grades'} icon="classes">
        <p>
          {meta?.school_year || 'Save drafts, then submit the class when the encode window is open.'}
          {summary ? ` ${summary.encoded} of ${summary.roster} encoded.` : ''}
        </p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          {summary ? (
            <>
              <span className={`studio-chip ${progressChipClass(summary.progress)}`}>{summary.progress_label}</span>
              {summary.workflow_label ? <span className="studio-chip is-approved">{summary.workflow_label}</span> : null}
            </>
          ) : null}
        </div>
      </PageHead>
      <div className="studio-actions">
        <Link to="/teacher/classes">Back to classes</Link>
        <Link to={`/teacher/classes/${assignmentId}/records`}>Records</Link>
      </div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <DutyTermTabs
        terms={terms}
        termId={termId}
        onChange={setTermId}
        label={(term) => (term.encode_open === false ? `${term.label} · closed` : term.label)}
        empty="This subject has no term scheduled yet. The Head Teacher sets it in the term plan."
      />

      {terms.length ? (
        <>
          {encodeOpen ? null : <p className="alert alert-error">The encode window for this term is closed.</p>}

          <details className="studio-help card" open={showHelp} onToggle={(event) => setShowHelp(event.target.open)}>
            <summary>How to submit grades &amp; request a correction</summary>
            <div className="studio-help-body">
              <p>
                <strong>Submitting grades:</strong> type each student's grade in the Grade column, then click{' '}
                <strong>Save</strong> on that row. Once every student you want to send is saved, click{' '}
                <strong>Submit class grades</strong> above the table to send the drafts for approval.
              </p>
              <p>
                <strong>Requesting a correction:</strong> for a grade that has already been submitted, approved, or
                released, click <strong>Request correction</strong> on that row. A pop-up will open where you enter the
                corrected score and your reason — short or long, it's up to you — then click <strong>Send request</strong>.
              </p>
            </div>
          </details>

          <label className="studio-search">
            <span className="desk-line">
              <LineMark name="search" size={14} />
              Search
            </span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or LRN" />
          </label>

          {students.length === 0 ? (
            <p className="card studio-panel studio-empty">No students are placed in this section yet.</p>
          ) : (
            <section className="card studio-panel studio-table-wrap">
              <div className="studio-actions studio-table-actions">
                <button
                  className="btn"
                  type="button"
                  disabled={submitting || !encodeOpen || !students.some((row) => row.status === 'draft')}
                  onClick={submitClass}
                >
                  {submitting ? 'Submitting…' : 'Submit class grades'}
                </button>
              </div>
              {summary?.missing ? (
                <p className="studio-empty">
                  {summary.missing} student{summary.missing === 1 ? ' has' : 's have'} no score. Submit will send only encoded drafts.
                </p>
              ) : null}
              {visible.length === 0 ? <p className="studio-empty">No students match that search.</p> : null}
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>LRN</th>
                    <th>Grade</th>
                    <th>Updated</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((row) => (
                    <tr key={row.student_id}>
                      <td>
                        <span className="desk-line">
                          <LineMark name="user" size={14} />
                          {row.name}
                        </span>
                      </td>
                        <td>{row.lrn}</td>
                        <td>
                          <input
                            className="studio-score"
                            inputMode="decimal"
                            value={scores[row.student_id] ?? ''}
                            disabled={!(row.editable && encodeOpen)}
                            onChange={(event) =>
                              setScores((current) => ({ ...current, [row.student_id]: event.target.value }))
                            }
                          />
                        </td>
                        <td>{when(row.updated_at) || '—'}</td>
                        <td>
                          <span className={`studio-status ${statusClass(row.status)}`}>
                            <LineMark name={gradeStatusIcon(row.status)} size={14} />
                            {row.status || 'Not encoded'}
                          </span>
                        </td>
                        <td>
                          {row.editable && encodeOpen ? (
                            <button className="btn" type="button" disabled={busyId === row.student_id} onClick={() => saveRow(row)}>
                              {busyId === row.student_id ? 'Saving…' : 'Save'}
                            </button>
                          ) : row.correction_pending ? (
                            'Correction pending'
                          ) : row.can_correct ? (
                            <button className="btn btn-secondary" type="button" onClick={() => openCorrection(row)}>
                              Request correction
                            </button>
                          ) : row.editable ? (
                            'Window closed'
                          ) : (
                            row.status || '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
            </section>
          )}

          {correctionRow ? (
            <div className="studio-modal-backdrop" onClick={closeCorrection}>
              <div className="card studio-panel studio-modal" onClick={(event) => event.stopPropagation()}>
                <h2>Request correction · {correctionRow.name}</h2>
                <p className="studio-table-sub">Current score: {correctionRow.score ?? '—'}</p>
                <label className="form-field">
                  <span>Corrected score</span>
                  <input
                    inputMode="decimal"
                    value={correctionScore}
                    onChange={(event) => setCorrectionScore(event.target.value)}
                  />
                </label>
                <label className="form-field">
                  <span>Reason</span>
                  <textarea
                    rows={4}
                    value={correctReason}
                    onChange={(event) => setCorrectReason(event.target.value)}
                    placeholder="Explain why this grade needs correction (a short or long reason is fine)"
                  />
                </label>
                <div className="studio-actions">
                  <button
                    className="btn btn-secondary"
                    type="button"
                    onClick={closeCorrection}
                    disabled={busyId === correctionRow.student_id}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn"
                    type="button"
                    onClick={sendCorrection}
                    disabled={busyId === correctionRow.student_id || !correctReason.trim()}
                  >
                    {busyId === correctionRow.student_id ? 'Sending…' : 'Send request'}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
