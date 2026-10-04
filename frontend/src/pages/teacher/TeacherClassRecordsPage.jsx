import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { fetchClassGrades, fetchGradeTimeline, fetchTeacherAssignments, fetchTerms } from '../../services/teacherService';
import { when } from '../../utils/when';
import DutyTermTabs from './DutyTermTabs';
import { defaultTermId, dutyTerms } from './dutyTerms';

export default function TeacherClassRecordsPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const [meta, setMeta] = useState(null);
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [students, setStudents] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_encode) {
          throw new Error('You cannot open records for that class.');
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
    fetchClassGrades(assignmentId, termId)
      .then((data) => {
        if (cancelled) return;
        setMeta(data.assignment);
        setStudents(data.students || []);
        setSelectedId(null);
        setEvents([]);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [assignmentId, termId]);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return students;
    return students.filter((row) => [row.name, row.lrn, row.status].join(' ').toLowerCase().includes(needle));
  }, [query, students]);

  async function openRow(student) {
    setSelectedId(student.student_id);
    setBusy(true);
    setError('');
    try {
      const data = await fetchGradeTimeline({
        assignment: assignmentId,
        term: termId,
        student: student.student_id,
      });
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading records…" />;

  const selected = students.find((row) => row.student_id === selectedId);
  const heading = meta?.section_label || meta?.section || 'Records';

  return (
    <div className="desk studio">
      <PageHead kicker={heading} title={meta ? `${meta.subject} records` : 'Class records'} icon="history">
        <p>Search the section, then open a student to see this term’s encode history.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
        </div>
      </PageHead>
      <p>
        <Link to={`/teacher/classes/${assignmentId}`}>Back to encode</Link>
      </p>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <DutyTermTabs
        terms={terms}
        termId={termId}
        onChange={setTermId}
        empty="This subject has no term scheduled yet. The Head Teacher sets it in the term plan."
      />

      {terms.length ? (
        <>
          <label className="studio-search">
            <span className="desk-line">
              <LineMark name="search" size={14} />
              Search
            </span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or LRN" />
          </label>

          <section className="card studio-panel studio-table-wrap">
            {rows.length === 0 ? (
              <p className="studio-empty">No students match that search.</p>
            ) : (
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>LRN</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.student_id} className={row.student_id === selectedId ? 'is-open' : ''}>
                      <td>
                        <button className="studio-link desk-line" type="button" onClick={() => openRow(row)}>
                          <LineMark name="user" size={14} />
                          {row.name}
                        </button>
                      </td>
                      <td>{row.lrn}</td>
                      <td>{row.score ?? '—'}</td>
                      <td>{row.status || 'Not encoded'}</td>
                      <td>{when(row.updated_at) || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card studio-panel">
            <h2>
              <LineMark name="history" />
              {selected ? selected.name : 'Term timeline'}
            </h2>
            {!selected ? <p className="studio-empty">Click a student name to open this term’s history.</p> : null}
            {selected && busy ? <p className="studio-empty">Loading timeline…</p> : null}
            {selected && !busy && events.length === 0 ? (
              <p className="studio-empty">No encoded history for this student in this term yet.</p>
            ) : null}
            {events.map((row) => (
              <article className="studio-event" key={row.id}>
                <p className="studio-kicker">{when(row.changed_at)}</p>
                <h2>
                  {row.previous_score || '—'} → {row.new_score || '—'}
                </h2>
                <p>
                  {row.from_status || 'new'} to {row.to_status} · {row.changed_by || 'System'}
                  {row.reason ? ` · ${row.reason}` : ''}
                </p>
              </article>
            ))}
          </section>
        </>
      ) : null}
    </div>
  );
}
