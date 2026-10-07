import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../../../components/DeskMark/DeskMark';
import Icon from '../../../components/Icon/Icon';
import MatchLabel from '../../../components/Guidance/MatchLabel';
import { fetchGuidance } from '../../../services/guidanceService';
import '../../../components/Guidance/Guidance.css';

// Recommendations need shown grades in at least this many skill areas (MIN_SKILLS in apps/ml/recommender.py).
const MIN_SKILLS = 3;

// Where the student stands: the three things a recommendation needs, each done or still to do.
function steps(data) {
  const skills = data.recommendation?.skills || [];
  const surveyDone = data.assessment.status === 'completed';
  return [
    { key: 'grades', label: 'Grades shown', done: skills.length >= MIN_SKILLS },
    { key: 'consent', label: 'Agreed to recommendations', done: Boolean(data.consent.assessment) },
    { key: 'survey', label: 'Interest survey', done: surveyDone, hidden: !data.assessment.open && !surveyDone },
  ].filter((step) => !step.hidden);
}

// The one action that moves the student forward, so the card always leads somewhere useful.
function nextAction(data) {
  if (!data.consent.assessment) return { to: '/student/guidance', label: 'Start college recommendation' };
  if (data.assessment.status === 'in_progress') return { to: '/student/guidance/assessment', label: 'Continue the interest survey' };
  if (data.assessment.open && data.assessment.status === 'not_started') {
    return { to: '/student/guidance/assessment', label: 'Take the interest survey' };
  }
  return { to: '/student/guidance', label: 'Open college recommendation' };
}

// A compact view of the student's saved recommendation for the overview and grades pages.
export default function GuidanceSummaryCard() {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetchGuidance()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  const recommendation = data?.recommendation;
  const action = data ? nextAction(data) : { to: '/student/guidance', label: 'Open college recommendation' };

  return (
    <article className="card desk-tile gd-summary-card">
      <h2>
        <span className="desk-title">
          <DeskMark name="guidance" size={16} />
          College recommendation
        </span>
      </h2>

      {failed ? <p className="desk-empty">College recommendation could not be loaded right now.</p> : null}
      {!data && !failed ? <p className="desk-empty">Loading your recommendation…</p> : null}

      {data ? (
        <ul className="gd-progress" aria-label="Your recommendation steps">
          {steps(data).map((step) => (
            <li key={step.key} className={step.done ? 'is-done' : undefined}>
              <span className="gd-progress-mark" aria-hidden="true">
                {step.done ? <Icon name="check" size={12} /> : null}
              </span>
              {step.label}
              <span className="gd-sr">{step.done ? ' (done)' : ' (to do)'}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {recommendation?.ready ? (
        <ol className="gd-summary-list">
          {recommendation.primary.map((item) => (
            <li key={item.program.code}>
              <span className="gd-summary-rank" aria-hidden="true">
                {item.rank}
              </span>
              <span className="gd-summary-name">
                <strong>{item.program.name}</strong>
                {item.program.family ? <small>{item.program.family}</small> : null}
              </span>
              <MatchLabel label={item.label} />
            </li>
          ))}
        </ol>
      ) : null}

      {recommendation && !recommendation.ready ? <p className="desk-empty">{recommendation.not_ready}</p> : null}
      {data && !data.consent.assessment ? (
        <p className="desk-empty">Agree to recommendations and answer a short interest survey to make these matches stronger.</p>
      ) : null}
      {recommendation?.ready ? <p className="gd-note">{recommendation.method_label}. A starting point, not a decision. It is not trained on past graduates.</p> : null}

      <Link className="btn btn-secondary gd-summary-action" to={action.to}>
        {action.label}
      </Link>
    </article>
  );
}
