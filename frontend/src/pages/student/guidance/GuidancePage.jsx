import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import CompareTray from '../../../components/Guidance/CompareTray';
import InterestProfile from '../../../components/Guidance/InterestProfile';
import RecommendationView from '../../../components/Guidance/RecommendationView';
import useCompare from '../../../components/Guidance/useCompare';
import { grade } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import { fetchGuidance } from '../../../services/guidanceService';
import ConsentPanel from './ConsentPanel';
import PrivacyControls from './PrivacyControls';
import '../../../components/Guidance/Guidance.css';

function Steps({ data }) {
  const recommendation = data.recommendation;
  const steps = [
    { done: recommendation.ready, text: recommendation.ready ? 'Academic profile complete' : 'Academic profile in progress' },
    {
      done: data.assessment.status === 'completed',
      text: data.assessment.status === 'completed' ? 'Interest assessment complete' : 'Interest assessment not done',
    },
    { done: recommendation.ready, text: recommendation.ready ? 'Recommendation ready' : 'Recommendation waiting' },
  ];
  return (
    <ul className="gd-steps">
      {steps.map((step) => (
        <li key={step.text} className={step.done ? '' : 'is-todo'}>
          {step.done ? '✓ ' : ''}
          {step.text}
        </li>
      ))}
    </ul>
  );
}

function AssessmentPrompt({ assessment }) {
  if (!assessment.open) {
    return <p className="card gd-panel gd-note">The interest assessment opens soon. Your matches below use your grades and strand for now.</p>;
  }
  const started = assessment.status === 'in_progress';
  return (
    <section className="card gd-panel">
      <div className="gd-section-head">
        <h2>{started ? 'Finish your interest assessment' : 'Add your interests'}</h2>
        <p>{assessment.questions} questions · about 5 to 8 minutes · no right or wrong answers</p>
      </div>
      <p className="gd-note">
        Your interests make up one of the three parts of your matches. Until you answer, every program is marked Limited Evidence.
      </p>
      <div className="gd-actions">
        <Link className="btn" to="/student/guidance/assessment">
          {started ? 'Continue the assessment' : 'Start the assessment'}
        </Link>
      </div>
    </section>
  );
}

export default function GuidancePage() {
  const compare = useCompare();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchGuidance()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (!data && !error) return <Loading label="Preparing your college recommendation…" />;
  if (!data) return <p className="alert alert-error">{error}</p>;

  const { recommendation, consent, assessment } = data;
  const skills = recommendation.skills || [];

  return (
    <div className="desk gd-page">
      <header className="gd-hero">
        <h1>Your College Program Matches</h1>
        <p>
          Based on your approved Grade 11–12 records, your SHS strand and your career-interest assessment. The list is
          an ML recommendation: a starting point for planning, not a decision.
        </p>
        <Steps data={data} />
        <span className="gd-method">Method: {recommendation.method_label}</span>
      </header>

      {consent.assessment ? (
        assessment.status === 'completed' ? null : <AssessmentPrompt assessment={assessment} />
      ) : (
        <ConsentPanel consent={consent} onChange={setData} />
      )}

      <RecommendationView recommendation={recommendation} programPath="/student/guidance/programs" compare={compare} />

      <div className="gd-actions">
        <Link className="btn btn-secondary" to="/student/guidance/programs">
          Browse all programs
        </Link>
        {assessment.status === 'completed' ? (
          <Link className="btn btn-secondary" to="/student/guidance/assessment">
            Retake the assessment
          </Link>
        ) : null}
      </div>

      <div className="gd-split">
        <section className="card gd-panel" aria-labelledby="gd-interest-title">
          <h2 id="gd-interest-title">Your interest profile</h2>
          <InterestProfile scores={recommendation.interest} />
        </section>
        <section className="card gd-panel" aria-labelledby="gd-skills-title">
          <h2 id="gd-skills-title">Your skill areas</h2>
          {skills.length ? (
            <dl className="gd-facts">
              {skills.map((row) => (
                <div key={row.key}>
                  <dt>{row.label}</dt>
                  <dd>{grade(row.value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="gd-note">Skill averages appear once your adviser shows your grades.</p>
          )}
          {recommendation.needs.length ? (
            <p className="gd-note">Grades in {recommendation.needs.join(', ')} would let more programs be checked.</p>
          ) : null}
          {recommendation.strand_group ? <p className="gd-note">Your strand group: {recommendation.strand_group}</p> : null}
        </section>
      </div>

      {consent.assessment ? <PrivacyControls consent={consent} onChange={setData} /> : null}
      <p className="gd-note">
        Advisory only. Recommendations suggest programs that align with your evidence; they do not guarantee admission or success.
      </p>
      <CompareTray compare={compare} comparePath="/student/guidance/compare" />
    </div>
  );
}
