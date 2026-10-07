import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import { completeAssessment, fetchAssessment, saveAnswer, startAssessment } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';
import '../../../components/Guidance/Guidance.css';
import './AssessmentPage.css';

const SCALE = [
  { value: 1, label: 'Definitely not' },
  { value: 2, label: 'Probably not' },
  { value: 3, label: 'Unsure' },
  { value: 4, label: 'Probably yes' },
  { value: 5, label: 'Definitely yes' },
];

function Intro({ instrument, started, busy, onStart }) {
  return (
    <section className="card gd-panel">
      <div className="gd-stats">
        <div className="gd-stat">
          <strong>{instrument.questions.length}</strong>
          <span>Questions in total</span>
        </div>
        <div className="gd-stat">
          <strong>5–8 min</strong>
          <span>Usual time. You can pause and continue later</span>
        </div>
        <div className="gd-stat">
          <strong>Same</strong>
          <span>For every student, whatever your strand or course idea</span>
        </div>
        <div className="gd-stat">
          <strong>None</strong>
          <span>Right or wrong answers. It is not graded</span>
        </div>
      </div>
      <p className="gd-note">
        Each question asks whether you would enjoy an activity you might do now or later. Answer for yourself, not whether you could do it as a job today.
      </p>
      <div className="gd-actions">
        <button className="btn" type="button" disabled={busy} onClick={onStart}>
          {started ? 'Continue' : 'Start the assessment'}
        </button>
        <Link className="btn btn-secondary" to="/student/guidance">
          Back to my matches
        </Link>
      </div>
    </section>
  );
}

export default function AssessmentPage() {
  const navigate = useNavigate();
  const legendRef = useRef(null);
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [index, setIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAssessment()
      .then((payload) => {
        setData(payload);
        setAnswers(payload.attempt?.answers || {});
      })
      .catch((err) => setError(firstApiError(err)));
  }, []);

  useEffect(() => {
    if (running) legendRef.current?.focus();
  }, [index, running]);

  if (!data && !error) return <Loading label="Loading the assessment…" />;

  const instrument = data?.instrument;
  const questions = instrument?.questions || [];
  const question = questions[index];
  const answered = questions.filter((row) => answers[row.id]).length;

  async function start() {
    setBusy(true);
    setError('');
    try {
      const payload = await startAssessment();
      const saved = payload.attempt?.answers || {};
      setAnswers(saved);
      const firstOpen = questions.findIndex((row) => !saved[row.id]);
      setIndex(firstOpen === -1 ? questions.length - 1 : firstOpen);
      setRunning(true);
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function choose(value) {
    setError('');
    const previous = answers[question.id];
    setAnswers((current) => ({ ...current, [question.id]: value }));
    try {
      await saveAnswer(question.id, value);
      if (index < questions.length - 1) setIndex(index + 1);
    } catch (err) {
      setAnswers((current) => ({ ...current, [question.id]: previous }));
      setError(firstApiError(err));
    }
  }

  async function finish() {
    setBusy(true);
    setError('');
    try {
      await completeAssessment();
      navigate('/student/guidance');
    } catch (err) {
      setError(firstApiError(err));
      const firstOpen = questions.findIndex((row) => !answers[row.id]);
      if (firstOpen !== -1) setIndex(firstOpen);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="desk gd-page">
      <PageHead kicker="College recommendation" title="Career interest assessment" icon="guidance">
        <p>Thirty questions about what you would enjoy as a senior high school student. It does not ask which course you want and does not depend on your SHS program.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      {!instrument ? (
        <p className="card gd-panel gd-note">
          {data ? 'The interest assessment is not open yet. Your adviser will tell you when it is. ' : ''}
          <Link to="/student/guidance">Back to my matches</Link>
        </p>
      ) : !running ? (
        <Intro instrument={instrument} started={Boolean(data.attempt)} busy={busy} onStart={start} />
      ) : (
        <section className="card gd-panel ia-question" aria-live="polite">
          <div className="gd-section-head">
            <h2>
              Question {index + 1} of {questions.length}
            </h2>
            <p>{answered} answered</p>
          </div>
          <div
            className="ia-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={questions.length}
            aria-valuenow={answered}
            aria-label="Questions answered"
          >
            <i style={{ width: `${(answered / questions.length) * 100}%` }} />
          </div>
          <fieldset className="ia-scale">
            <legend ref={legendRef} tabIndex={-1}>
              {question.text}
            </legend>
            {SCALE.map((option) => (
              <label key={option.value} className={answers[question.id] === option.value ? 'is-picked' : ''}>
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={option.value}
                  checked={answers[question.id] === option.value}
                  onChange={() => choose(option.value)}
                />
                <span className="ia-dot" aria-hidden="true" />
                {option.label}
              </label>
            ))}
          </fieldset>
          <div className="ia-nav">
            <button className="btn btn-secondary" type="button" disabled={index === 0} onClick={() => setIndex(index - 1)}>
              Back
            </button>
            {index < questions.length - 1 ? (
              <button
                className="btn btn-secondary"
                type="button"
                disabled={!answers[question.id]}
                onClick={() => setIndex(index + 1)}
              >
                Next
              </button>
            ) : (
              <button className="btn" type="button" disabled={busy || answered < questions.length} onClick={finish}>
                {busy ? 'Saving…' : 'Finish and see my matches'}
              </button>
            )}
          </div>
          <p className="gd-note">Your answers are saved as you go. You can leave and continue later.</p>
        </section>
      )}

      {instrument ? (
        <p className="gd-note">
          Based on the {instrument.name}. {instrument.attribution}{' '}
          <a href={instrument.license_url} target="_blank" rel="noopener noreferrer">
            License
          </a>
        </p>
      ) : null}
    </div>
  );
}
