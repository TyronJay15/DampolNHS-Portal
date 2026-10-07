import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import InterestProfile from '../../../components/Guidance/InterestProfile';
import RecommendationView from '../../../components/Guidance/RecommendationView';
import { formatDate } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import {
  addAdviserNote,
  addAdviserRecommendation,
  fetchAdvisee,
  fetchCatalog,
  recordOutcome,
} from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';
import '../../../components/Guidance/Guidance.css';

function ProgramSelect({ id, programs, value, onChange }) {
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)} required>
      <option value="">Choose a program</option>
      {programs.map((program) => (
        <option key={program.code} value={program.code}>
          {program.name}
        </option>
      ))}
    </select>
  );
}

// One student's guidance for their adviser. The system result is read-only; the adviser's own view is a
// separate record, so research data stays intact.
export default function AdviseeGuidancePage() {
  const { assignmentId, studentId } = useParams();
  const [data, setData] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [note, setNote] = useState('');
  const [pick, setPick] = useState({ program: '', reason: '' });
  const [outcome, setOutcome] = useState('');

  useEffect(() => {
    Promise.all([fetchAdvisee(assignmentId, studentId), fetchCatalog()])
      .then(([review, catalog]) => {
        setData(review);
        setPrograms(catalog.programs);
      })
      .catch((err) => setError(err.status === 404 ? 'This student is not in your advisory section.' : err.message));
  }, [assignmentId, studentId]);

  async function save(kind, request, reset) {
    setBusy(kind);
    setError('');
    try {
      setData(await request());
      reset();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy('');
    }
  }

  if (!data && !error) return <Loading label="Loading the student's recommendation…" />;

  const recommendation = data?.recommendation;
  const versions = recommendation?.versions;
  return (
    <div className="desk studio gd-page">
      <PageHead kicker={data?.section?.label || 'Advisory'} title={data ? data.student.name : 'College recommendation'} icon="guidance">
        <p>Review the result with the student. Your recommendation and notes are saved separately and never change it.</p>
      </PageHead>
      <div className="studio-actions">
        <Link to={`/teacher/advisory/${assignmentId}/guidance`}>Back to the section</Link>
      </div>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {data ? (
        <>
          <div className="gd-actions">
            <span className={`gd-pill${data.consent.assessment ? ' is-ok' : ''}`}>
              Consent {data.consent.assessment ? 'given' : 'not given'}
            </span>
            <span className={`gd-pill${data.assessment.status === 'completed' ? ' is-ok' : ''}`}>
              Assessment {data.assessment.status === 'completed' ? `done ${formatDate(data.assessment.completed_at)}` : 'not done'}
            </span>
            <span className="gd-pill is-strong">{recommendation.method_label}</span>
          </div>

          <section className="desk" aria-labelledby="gd-system-title">
            <div className="gd-section-head">
              <h2 id="gd-system-title">System recommendation (read-only)</h2>
              <p>
                {formatDate(recommendation.created_at)} · settings v{versions.config ?? '—'} · assessment v
                {versions.instrument ?? '—'}
              </p>
            </div>
            <RecommendationView recommendation={recommendation} />
          </section>

          <div className="gd-split">
            <section className="card gd-panel" aria-labelledby="gd-adviser-interest">
              <h2 id="gd-adviser-interest">Interest profile</h2>
              <InterestProfile scores={recommendation.interest} />
            </section>

            <section className="card gd-panel" aria-labelledby="gd-adviser-pick">
              <h2 id="gd-adviser-pick">Your recommendation</h2>
              <form
                className="desk"
                onSubmit={(event) => {
                  event.preventDefault();
                  save('pick', () => addAdviserRecommendation(assignmentId, studentId, pick), () => setPick({ program: '', reason: '' }));
                }}
              >
                <label className="form-field" htmlFor="gd-pick-program">
                  <span>Program</span>
                  <ProgramSelect id="gd-pick-program" programs={programs} value={pick.program} onChange={(program) => setPick({ ...pick, program })} />
                </label>
                <label className="form-field" htmlFor="gd-pick-reason">
                  <span>Reason</span>
                  <textarea
                    id="gd-pick-reason"
                    maxLength={1000}
                    required
                    value={pick.reason}
                    onChange={(event) => setPick({ ...pick, reason: event.target.value })}
                  />
                </label>
                <button className="btn" type="submit" disabled={busy === 'pick'}>
                  {busy === 'pick' ? 'Saving…' : 'Save my recommendation'}
                </button>
              </form>
              {data.adviser_recommendations.length ? (
                <ul className="gd-card-why">
                  {data.adviser_recommendations.map((row) => (
                    <li key={row.id}>
                      <strong>{row.program.name}</strong> · {formatDate(row.created_at)} · {row.adviser}: {row.reason}
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          </div>

          <div className="gd-split">
            <section className="card gd-panel" aria-labelledby="gd-notes-title">
              <h2 id="gd-notes-title">Notes</h2>
              <form
                className="desk"
                onSubmit={(event) => {
                  event.preventDefault();
                  save('note', () => addAdviserNote(assignmentId, studentId, note), () => setNote(''));
                }}
              >
                <label className="form-field" htmlFor="gd-note">
                  <span>New note (not shown to the student)</span>
                  <textarea id="gd-note" maxLength={2000} required value={note} onChange={(event) => setNote(event.target.value)} />
                </label>
                <button className="btn btn-secondary" type="submit" disabled={busy === 'note'}>
                  {busy === 'note' ? 'Saving…' : 'Add note'}
                </button>
              </form>
              {data.notes.length ? (
                <ul className="gd-card-why">
                  {data.notes.map((row) => (
                    <li key={row.id}>
                      {formatDate(row.created_at)} · {row.author}: {row.body}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="gd-note">No notes yet.</p>
              )}
            </section>

            <section className="card gd-panel" aria-labelledby="gd-outcome-title">
              <h2 id="gd-outcome-title">Program entered after graduation</h2>
              {data.outcome ? (
                <p className="gd-note">
                  Recorded: <strong>{data.outcome.program.name}</strong> ·{' '}
                  {data.outcome.status === 'validated' ? 'validated, used for training' : 'waiting for a second person to validate'}
                </p>
              ) : (
                <p className="gd-note">Record this only when you know the program the graduate actually entered.</p>
              )}
              {data.outcome?.status === 'validated' ? null : (
                <form
                  className="desk"
                  onSubmit={(event) => {
                    event.preventDefault();
                    save('outcome', () => recordOutcome(assignmentId, studentId, outcome), () => setOutcome(''));
                  }}
                >
                  <label className="form-field" htmlFor="gd-outcome">
                    <span>Program entered</span>
                    <ProgramSelect id="gd-outcome" programs={programs} value={outcome} onChange={setOutcome} />
                  </label>
                  <button className="btn btn-secondary" type="submit" disabled={busy === 'outcome'}>
                    {busy === 'outcome' ? 'Saving…' : data.outcome ? 'Update the outcome' : 'Record the outcome'}
                  </button>
                </form>
              )}
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
