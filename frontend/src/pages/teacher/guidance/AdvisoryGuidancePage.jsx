import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import MatchLabel from '../../../components/Guidance/MatchLabel';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import { fetchAdvisoryGuidance } from '../../../services/guidanceService';
import '../../../components/Guidance/Guidance.css';

const ASSESSMENT = {
  completed: { text: 'Done', tone: 'is-ok' },
  in_progress: { text: 'In progress', tone: 'is-warn' },
  not_started: { text: 'Not started', tone: '' },
};

// The adviser's own section: each student's consent, assessment, first recommended program and outcome.
export default function AdvisoryGuidancePage() {
  const { assignmentId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAdvisoryGuidance(assignmentId)
      .then(setData)
      .catch((err) => setError(err.status === 404 ? 'This advisory section is not assigned to you.' : err.message));
  }, [assignmentId]);

  if (!data && !error) return <Loading label="Loading college recommendation…" />;

  return (
    <div className="desk studio gd-page">
      <PageHead kicker={data?.section?.school_year || 'Advisory'} title={`College recommendation · ${data?.section?.label || ''}`} icon="guidance">
        <p>Use each student's results to start a conversation. Results are a starting point, never a decision.</p>
      </PageHead>
      <div className="studio-actions">
        <Link to={`/teacher/advisory/${assignmentId}`}>Back to the section</Link>
      </div>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {data ? (
        <div className="card studio-table-wrap">
          <table className="studio-table gd-table">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Consent</th>
                <th scope="col">Assessment</th>
                <th scope="col">First program</th>
                <th scope="col">Outcome</th>
                <th scope="col">
                  <span className="gd-sr">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.students.length ? (
                data.students.map((row) => {
                  const assessment = ASSESSMENT[row.assessment] || ASSESSMENT.not_started;
                  return (
                    <tr key={row.student_id}>
                      <td>{row.name}</td>
                      <td>
                        <span className={`gd-pill${row.consent ? ' is-ok' : ''}`}>{row.consent ? 'Given' : 'Not given'}</span>
                      </td>
                      <td>
                        <span className={`gd-pill ${assessment.tone}`}>{assessment.text}</span>
                      </td>
                      <td>
                        {row.recommendation ? (
                          <div className="gd-actions">
                            <span>{row.recommendation.program}</span>
                            <MatchLabel label={row.recommendation.label} />
                          </div>
                        ) : (
                          <span className="gd-note">Not generated yet</span>
                        )}
                      </td>
                      <td>
                        {row.outcome ? (
                          <span className={`gd-pill${row.outcome.status === 'validated' ? ' is-ok' : ' is-warn'}`}>
                            {row.outcome.program} · {row.outcome.status === 'validated' ? 'validated' : 'awaiting validation'}
                          </span>
                        ) : (
                          <span className="gd-note">Not recorded</span>
                        )}
                      </td>
                      <td>
                        <Link className="btn btn-secondary" to={`/teacher/advisory/${assignmentId}/guidance/${row.student_id}`}>
                          Review
                        </Link>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6}>No students are placed in this section yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
