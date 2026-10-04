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

// A subject belongs to a term when the term plan schedules it there, or a score was already shown there.
function inTerm(subject, term, scores) {
  return (subject.terms || []).includes(term.number) || Boolean(scores[`${subject.id}:${term.number}`]);
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

function TermTable({ term, subjects, scores, average }) {
  const rows = subjects.filter((subject) => inTerm(subject, term, scores));
  return (
    <div className="student-grade-table-wrap">
      <table className="student-grade-table">
        <thead>
          <tr>
            <th>Subject</th>
            <th className="student-grade-score">{term.label}</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={2} className="student-grade-pending">
                No subjects are scheduled in {term.label}.
              </td>
            </tr>
          ) : null}
          {rows.map((subject) => {
            const score = scores[`${subject.id}:${term.number}`];
            return (
              <tr key={subject.id || subject.code || subject.name}>
                <td>
                  <span className="desk-line">
                    <LineMark name="classes" size={14} />
                    {subject.name}
                  </span>
                </td>
                <td className="student-grade-score">
                  <span className={score ? '' : 'student-grade-pending'}>{score || 'Not yet posted'}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">
              <span className="desk-line">
                <LineMark name="forecast" size={14} />
                {term.label} average
              </span>
            </th>
            <td className="student-grade-score student-grade-avg student-grade-overall">
              <AverageCell summary={average} unit="subjects" />
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function YearTable({ card, scores, subjectAverages, termAverages }) {
  return (
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
              {card.terms.map((term) => {
                const score = scores[`${subject.id}:${term.number}`];
                return (
                  <td key={term.id} className="student-grade-score">
                    {inTerm(subject, term, scores) ? (
                      <span className={score ? '' : 'student-grade-pending'}>{score || 'Not yet posted'}</span>
                    ) : (
                      <span className="student-grade-off" title={`Not scheduled in ${term.label}`}>
                        —
                      </span>
                    )}
                  </td>
                );
              })}
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
  const [view, setView] = useState('all');

  useEffect(() => {
    fetchStudentGrades()
      .then((data) => {
        const current = (data.terms || []).find((term) => term.is_current);
        setView(current ? current.number : 'all');
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
        });
      })
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
  const term = card.terms.find((row) => row.number === view);
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
              <div className="student-term-tabs" role="tablist" aria-label="Report card view">
                {card.terms.map((term) => (
                  <button
                    key={term.id}
                    type="button"
                    role="tab"
                    aria-selected={view === term.number}
                    className={view === term.number ? 'is-active' : ''}
                    onClick={() => setView(term.number)}
                  >
                    {term.label}
                  </button>
                ))}
                <button
                  type="button"
                  role="tab"
                  aria-selected={view === 'all'}
                  className={view === 'all' ? 'is-active' : ''}
                  onClick={() => setView('all')}
                >
                  Whole year
                </button>
              </div>
              {term ? <TermTable term={term} subjects={card.subjects} scores={scores} average={termAverages[term.number]} /> : null}
              {view === 'all' ? (
                <YearTable
                  card={card}
                  scores={scores}
                  subjectAverages={subjectAverages}
                  termAverages={termAverages}
                />
              ) : null}
              <p className="student-grade-foot">
                Each term lists only the subjects scheduled in it. Averages use shown scores only, so they move as
                more terms are released.
              </p>
            </>
          ) : null}
        </section>

        <RecommendationPanel rec={rec} />
      </div>
    </div>
  );
}
