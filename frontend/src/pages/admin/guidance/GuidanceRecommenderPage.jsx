import { useEffect, useState } from 'react';
import Loading from '../../../components/Loading/Loading';
import MetricStrip from '../../../components/MetricStrip/MetricStrip';
import { fetchRecommenderStatus } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

export default function GuidanceRecommenderPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRecommenderStatus()
      .then(setData)
      .catch((err) => setError(firstApiError(err) || err.message));
  }, []);

  if (!data && !error) return <Loading label="Loading the recommender…" />;
  if (!data) return <p className="alert alert-error">{error}</p>;

  const totals = data.totals || {};
  const instrument = data.instrument;

  return (
    <>
      <MetricStrip
        items={[
          { key: 'method', label: 'Serving students', value: 'ML recommendation', icon: 'guidance', tone: 'green' },
          { key: 'agreed', label: 'Students who agreed', value: totals.assessment_consents ?? 0, icon: 'staff', tone: 'blue' },
          { key: 'surveys', label: 'Completed surveys', value: totals.completed_assessments ?? 0, icon: 'check', tone: 'purple' },
          { key: 'lists', label: 'Students with a match list', value: totals.students_with_recommendations ?? 0, icon: 'place', tone: 'gold' },
        ]}
      />

      <section className="card gd-panel" aria-labelledby="gd-live-title">
        <div className="gd-section-head">
          <h3 id="gd-live-title">What students receive</h3>
          <span className="gd-pill is-ok">Live</span>
        </div>
        <p className="gd-note">
          Each signed-in student is matched to college program profiles with k-nearest neighbors. The match uses that
          student's shown grades, SHS interest answers and strand. Strand is a last tie-break, not a gate. The list is an
          ML recommendation: a starting point, not a decision. It is not trained on past graduates.
        </p>
        {instrument ? (
          <p className="gd-note">
            Interest survey in use: {instrument.name}
            {instrument.version ? ` · version ${instrument.version}` : ''}.
          </p>
        ) : (
          <p className="gd-note">No interest survey is open yet. Open one from the Assessment tab.</p>
        )}
      </section>

      <section className="card gd-panel" aria-labelledby="gd-how-title">
        <h3 id="gd-how-title">How a program is ranked</h3>
        <p className="gd-note">
          <strong>Grades.</strong> Relative strengths across skill areas are compared with each program's expert profile.
          Closer programs rank higher.
        </p>
        <p className="gd-note">
          <strong>Interest.</strong> The SHS survey scores are compared with the program family's interest types.
        </p>
        <p className="gd-note">
          <strong>Evidence and floors.</strong> Programs whose key areas have grades come first. A below-benchmark count
          can move rank; it does not hide a program.
        </p>
        <p className="gd-note">
          <strong>Strand.</strong> A typical pathway for the student's strand only breaks remaining ties.
        </p>
      </section>
    </>
  );
}
