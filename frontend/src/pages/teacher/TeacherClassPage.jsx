import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { gradeStatusIcon } from '../../utils/gradeStatus';
import {
  encodeGrade,
  fetchClassGrades,
  fetchTeacherAssignments,
  fetchTerms,
  requestCorrection,
  submitClassGrades,
} from '../../services/teacherService';
import { when } from '../../utils/when';

function statusClass(status) {
  if (status === 'submitted') return 'is-submitted';
  if (status === 'approved') return 'is-approved';
  if (status === 'released') return 'is-released';
  return '';
}

export default function TeacherClassPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
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
  const [encodeOpen, setEncodeOpen] = useState(true);
  const [correctingId, setCorrectingId] = useState(null);
  const [correctReason, setCorrectReason] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_encode) {
          throw new Error('You cannot encode grades for that class.');
        }
        const termRows = await fetchTerms(assignment.school_year_id);
        const current = termRows.find((row) => row.is_current) || termRows[0];
        if (cancelled) return;
        setTerms(termRows);
        setTermId(current ? String(current.id) : '');
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
      setMessage(`Saved ${saved.name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function sendCorrection(student) {
    setBusyId(student.student_id);
    setMessage('');
    setError('');
    try {
      await requestCorrection({
        assignment: Number(assignmentId),
        grade: student.grade_id,
        proposed_score: scores[student.student_id],
        reason: correctReason,
      });
      const data = await fetchClassGrades(assignmentId, termId);
      setStudents(data.students || []);
      setCorrectingId(null);
      setCorrectReason('');
      setMessage(`Correction requested for ${student.name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function submitClass() {
    setSubmitting(true);
    setMessage('');
    setError('');
    try {
      const result = await submitClassGrades(Number(assignmentId), Number(termId));
      const data = await fetchClassGrades(assignmentId, termId);
      setStudents(data.students || []);
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
        <p>{meta?.school_year || 'Save drafts, then submit the class when the encode window is open.'}</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
        </div>
      </PageHead>
      <div className="studio-actions">
        <Link to="/teacher/classes">Back to classes</Link>
        <Link to={`/teacher/classes/${assignmentId}/records`}>Records</Link>
      </div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-tabs">
        {terms.map((term) => (
          <button
            key={term.id}
            type="button"
            className={String(term.id) === termId ? 'is-active' : ''}
            onClick={() => setTermId(String(term.id))}
          >
            {term.encode_open === false ? `${term.label} · closed` : term.label}
          </button>
        ))}
      </div>

      {encodeOpen ? null : <p className="alert alert-error">The encode window for this term is closed.</p>}

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
                        disabled={!(row.editable && encodeOpen) && correctingId !== row.student_id}
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
                      ) : row.can_correct && correctingId === row.student_id ? (
                        <span className="studio-actions">
                          <input
                            className="studio-score"
                            placeholder="Reason"
                            value={correctReason}
                            onChange={(event) => setCorrectReason(event.target.value)}
                          />
                          <button className="btn" type="button" disabled={busyId === row.student_id} onClick={() => sendCorrection(row)}>
                            Send
                          </button>
                        </span>
                      ) : row.can_correct ? (
                        <button className="btn btn-secondary" type="button" onClick={() => setCorrectingId(row.student_id)}>
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
    </div>
  );
}
