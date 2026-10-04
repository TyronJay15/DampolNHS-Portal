import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { cardStatusClass, cardStatusIcon, cardStatusLabel } from '../../utils/gradeStatus';
import { fetchAdvisory, fetchTeacherAssignments, fetchTerms } from '../../services/teacherService';
import DutyTermTabs from './DutyTermTabs';
import { defaultTermId, dutyTerms } from './dutyTerms';
import { genderLabel } from '../../utils/gender';

export default function TeacherAdvisoryRecordsPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [data, setData] = useState(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_advise) {
          throw new Error('You are not the adviser for that section.');
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
    fetchAdvisory(assignmentId, termId)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [assignmentId, termId]);

  const rows = useMemo(() => {
    const students = data?.students || [];
    const needle = query.trim().toLowerCase();
    if (!needle) return students;
    return students.filter((row) =>
      [row.name, row.lrn, row.guardian_name, row.contact_number].join(' ').toLowerCase().includes(needle),
    );
  }, [data, query]);

  if (loading) return <Loading label="Loading records…" />;

  return (
    <div className="desk studio">
      <PageHead
        kicker={data?.section?.program || data?.section?.grade_level || 'Advisory'}
        title={data?.assignment?.section ? `${data.assignment.section} records` : 'Advisory records'}
        icon="history"
      >
        <p>Read-only roster, card status, and recommendation for this advisory section.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
        </div>
      </PageHead>
      <p>
        <Link to={`/teacher/advisory/${assignmentId}`}>Back to advisory</Link>
      </p>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <DutyTermTabs
        terms={terms}
        termId={termId}
        onChange={setTermId}
        empty="No subject of this section is scheduled in any term yet. The Head Teacher sets it in the term plan."
      />

      {terms.length ? (
        <>
          <label className="studio-search">
            <span className="desk-line">
              <LineMark name="search" size={14} />
              Search
            </span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, LRN, or guardian" />
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
                    <th>Contact</th>
                    <th>Guardian</th>
                    <th>Card</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.student_id}>
                      <td>
                        <span className="desk-line">
                          <LineMark name="user" size={14} />
                          {row.name}
                        </span>
                        {row.gender ? <p className="studio-table-sub">{genderLabel(row.gender)}</p> : null}
                      </td>
                      <td>{row.lrn}</td>
                      <td>{row.contact_number || '—'}</td>
                      <td>
                        {row.guardian_name || '—'}
                        {row.guardian_contact ? ` · ${row.guardian_contact}` : ''}
                      </td>
                      <td>
                        <span className={`studio-status ${cardStatusClass(row)}`}>
                          <LineMark name={cardStatusIcon(row)} size={14} />
                          {cardStatusLabel(row)}
                        </span>
                      </td>
                      <td>{row.recommendation?.courses?.[0]?.name || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
