import { useEffect, useState } from 'react';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchSchoolYears } from '../../services/adminService';
import TermPlanPanel from './TermPlanPanel';

// Which terms each subject runs in, per school year. A future year can be planned before it is made current.
export default function HeadTermPlanPage() {
  const [years, setYears] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSchoolYears()
      .then(setYears)
      .catch((err) => setError(err.message));
  }, []);

  if (!years && !error) return <Loading label="Loading term plan…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Curriculum" title="Term plan" icon="year">
        <p>
          Set which terms each program subject runs in. A subject only appears to its teacher and students in those
          terms. New school years start from the Admin&apos;s default terms.
        </p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {years ? <TermPlanPanel years={years} /> : null}
    </div>
  );
}
