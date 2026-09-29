import { useEffect, useMemo, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { fetchStudentGrades } from '../../services/studentService';
import RecommendationPanel from './RecommendationPanel';
import './StudentStudio.css';

function scoreMap(grades) {
  const map = {};
  grades.forEach((row) => {
    map[`${row.subject_id}:${row.term_number}`] = row.score;
  });
  return map;
}

function summaryMap(rows, key) {
  const map = {};
  rows.forEach((row) => {
    map[row[key]] = row;
  });
  return map;
}

function AverageCell({ summary, unit }) {
  if (!summary?.average) return <>—</>;
  const partial = summary.included < summary.possible;
  return (
    <span className="student-avg">
      <strong>{summary.average}</strong>
      {partial ? (
        <small>
          {summary.included}/{summary.possible} {unit}
        </small>
      ) : null}
    </span>
  );
}

export default function StudentGradesPage() {
  const { user } = useAuth();
  const [card, setCard] = useState({
    terms: [],
    subjects: [],
    grades: [],
    subject_averages: [],
    term_averages: [],
    overall_average: null,
    school_year: '',
    recommendation: null,
    partial: false,
    coverage_note: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudentGrades()
      .then((data) =>
        setCard({
          terms: data.terms || [],
          subjects: data.subjects || [],
          grades: data.grades || [],
          subject_averages: data.subject_averages || [],
          term_averages: data.term_averages || [],
          overall_average: data.overall_average || null,
          school_year: data.school_year || '',
          recommendation: data.recommendation || null,
          partial: Boolean(data.partial),
          coverage_note: data.coverage_note || '',
        }),
      )
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const scores = useMemo(() => scoreMap(card.grades), [card.grades]);
  const subjectAverages = useMemo(
    () => summaryMap(card.subject_averages, 'subject_id'),
    [card.subject_averages],
  );
  const termAverages = useMemo(
    () => summaryMap(card.term_averages, 'term_number'),
    [card.term_averages],
  );

  if (loading) return <Loading label="Loading grades…" />;

  const hasGrid = card.subjects.length > 0 && card.terms.length > 0;
  const shownScores = card.grades.filter((row) => row.score != null && row.score !== '').length;
  const rec = card.recommendation;

  return (
    <div className="desk student-studio">
      <PageHead kicker={card.school_year || 'Report card'} title="Grades" icon="grades">
        <p>Only scores your adviser has shown are filled in. Subjects that are not posted yet stay marked as not yet posted.</p>
        <div className="student-hero-meta">
          <YearChip user={user} className="student-chip" />
        </div>
      </PageHead>
      {card.partial && card.coverage_note ? <p className="alert alert-info">{card.coverage_note}</p> : null}

      <div className="student-stats is-grades">
        <article className="card student-stat">
          <span className="desk-stat-top">
            <DeskMark name="year" size={16} />
            School year
          </span>
          <strong>{card.school_year || '—'}</strong>
        </article>
        <article className="card student-stat">
          <span className="desk-stat-top">
            <DeskMark name="classes" size={16} />
            Subjects
          </span>
          <strong>{card.subjects.length || '—'}</strong>
        </article>
        <article className="card student-stat">
          <span className="desk-stat-top">
            <DeskMark name="grades" size={16} />
            Shown scores
          </span>
          <strong>{shownScores}</strong>
        </article>
        <article className="card student-stat">
          <span className="desk-stat-top">
            <DeskMark name="grades" size={16} />
            General average
          </span>
          <strong>{card.overall_average?.average || '—'}</strong>
        </article>
        <article className="card student-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            College match
          </span>
          <strong>{rec?.ready ? 'Ready' : rec ? 'Waiting' : 'Reserved'}</strong>
        </article>
      </div>

      <div className="student-grade-layout">
        <section className="card student-panel">
          <h2>
            <LineMark name="grades" />
            Term scores
          </h2>
          {!error && !hasGrid ? <p className="student-empty">No subjects or terms are ready yet.</p> : null}
          {hasGrid ? (
            <>
              <div className="student-grade-table-wrap">
                <table className="student-grade-table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      {card.terms.map((term) => (
                        <th key={term.id} className="student-grade-score">
                          {term.label}
                        </th>
                      ))}
                      <th className="student-grade-score student-grade-avg">Subject average</th>
                    </tr>
                  </thead>
                  <tbody>
                    {card.subjects.map((subject) => (
                      <tr key={subject.id || subject.code || subject.name}>
                        <td>
                          <span className="desk-line">
                            <LineMark name="classes" size={14} />
                            {subject.name}
                          </span>
                        </td>
                        {card.terms.map((term) => (
                          <td key={term.id} className="student-grade-score">
                            <span className={scores[`${subject.id}:${term.number}`] ? '' : 'student-grade-pending'}>
                              {scores[`${subject.id}:${term.number}`] || 'Not yet posted'}
                            </span>
                          </td>
                        ))}
                        <td className="student-grade-score student-grade-avg">
                          <AverageCell summary={subjectAverages[subject.id]} unit="terms" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th scope="row">
                        <span className="desk-line">
                          <LineMark name="forecast" size={14} />
                          Term average
                        </span>
                      </th>
                      {card.terms.map((term) => (
                        <td key={term.id} className="student-grade-score student-grade-avg">
                          <AverageCell summary={termAverages[term.number]} unit="subjects" />
                        </td>
                      ))}
                      <td className="student-grade-score student-grade-avg student-grade-overall">
                        <AverageCell summary={card.overall_average} unit="scores" />
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <p className="student-grade-foot">
                Averages use shown scores only, so they move as more terms are released.
              </p>
            </>
          ) : null}
        </section>

        <RecommendationPanel rec={rec} />
      </div>
    </div>
  );
}
