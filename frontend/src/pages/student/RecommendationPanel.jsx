const PLACEHOLDERS = [
  { code: 'wait-1', name: 'Waiting for shown grades', reason: 'Your adviser must show the card before a match can appear.' },
  { code: 'wait-2', name: 'Second match', reason: 'Reserved for the next ranked college course.' },
  { code: 'wait-3', name: 'Third match', reason: 'Reserved for the third ranked college course.' },
];

function recCopy(rec) {
  if (!rec) {
    return {
      kicker: 'College match',
      title: 'Recommendation reserved',
      body: 'This space stays reserved. A college match appears automatically after your adviser shows your grades.',
    };
  }
  if (rec.ready) {
    return {
      kicker: rec.evidence === 'limited' ? 'Closest match so far' : 'College match',
      title: rec.courses?.[0]?.name || 'Top match ready',
      body: rec.summary || 'Ranked from the subjects your adviser has shown.',
    };
  }
  return {
    kicker: 'College match',
    title: 'Not enough shown grades yet',
    body: rec.summary || 'More shown subjects are needed before a college course can be ranked.',
  };
}

function joinLabels(labels) {
  return labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`;
}

// How much of a program's skill areas the student's own grades cover. Wording only; the API decides the status.
function evidenceCopy(evidence) {
  if (!evidence?.status) return '';
  const level = evidence.status === 'strong' ? 'Strong' : 'Limited';
  return `Evidence: ${level}. Based on ${evidence.observed} of ${evidence.total} relevant skill areas.`;
}

function needsCopy(coverage) {
  const labels = coverage?.needs || [];
  if (!labels.length) return '';
  const count = coverage.not_evaluated || 0;
  const subject = count ? `${count} other program${count === 1 ? '' : 's'}` : 'More programs';
  return `${subject} can be checked once you have grades in ${joinLabels(labels)}.`;
}

export default function RecommendationPanel({ rec, compact = false, className = '' }) {
  const copy = recCopy(rec);
  const courses = rec?.ready && rec.courses?.length ? rec.courses.slice(0, 3) : PLACEHOLDERS;
  const skills = rec?.skills || [];
  const needs = needsCopy(rec?.coverage);

  return (
    <section className={`card student-rec${compact ? ' is-compact' : ''}${rec?.ready ? ' is-ready' : ''}${className ? ` ${className}` : ''}`}>
      <header className="student-rec-head">
        <p>{copy.kicker}</p>
        <h2>{copy.title}</h2>
        <p className="student-rec-lede">{copy.body}</p>
      </header>

      {skills.length ? (
        <ul className="student-rec-skills">
          {skills.map((row) => (
            <li key={row.key || row.label}>
              <span>{row.label}</span>
              <strong>{row.average}</strong>
            </li>
          ))}
        </ul>
      ) : (
        <p className="student-rec-hint">Skill averages appear here once subjects are shown.</p>
      )}

      <ol className="student-rec-list">
        {courses.map((course, index) => (
          <li key={course.code || course.name || index} className={rec?.ready ? '' : 'is-wait'}>
            <em>{index + 1}</em>
            <div>
              <strong>{course.name}</strong>
              <span>{course.reason}</span>
              {evidenceCopy(course.evidence) ? <span>{evidenceCopy(course.evidence)}</span> : null}
            </div>
          </li>
        ))}
      </ol>

      {rec && !rec.ready ? (
        <p className="student-rec-hint">Evidence: Insufficient. More subject grades are needed to evaluate college programs.</p>
      ) : null}
      {needs ? <p className="student-rec-hint">{needs}</p> : null}
      <p className="student-rec-note">{rec?.advisory || 'Advisory. Based on subjects shown so far. Not an admission decision.'}</p>
    </section>
  );
}
