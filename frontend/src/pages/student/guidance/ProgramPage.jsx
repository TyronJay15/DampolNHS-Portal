import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import CompareTray from '../../../components/Guidance/CompareTray';
import FitChart from '../../../components/Guidance/FitChart';
import MatchLabel from '../../../components/Guidance/MatchLabel';
import useCompare from '../../../components/Guidance/useCompare';
import { formatDate } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import { fetchProgramFit } from '../../../services/guidanceService';
import '../../../components/Guidance/Guidance.css';

function chartRows(program, fit) {
  const mine = Object.fromEntries((fit.evidence?.strengths || []).map((row) => [row.key, row.student]));
  return program.profile.map((row) => ({
    key: row.domain,
    label: row.label,
    student: mine[row.domain] ?? null,
    expected: row.level,
    benchmark: row.benchmark,
    official: row.official,
  }));
}

function Fit({ program, fit }) {
  if (fit.status === 'not_checked') {
    return (
      <section className="card gd-panel">
        <h2>How you relate to this program</h2>
        <p className="gd-note">{fit.reason}</p>
        {fit.unchecked?.length ? <p className="gd-note">Grades in {fit.unchecked.join(', ')} would let it be checked.</p> : null}
      </section>
    );
  }
  if (fit.status !== 'evaluated') return null;
  return (
    <section className="card gd-panel">
      <div className="gd-section-head">
        <h2>How you relate to this program</h2>
        <MatchLabel label={fit.label} />
      </div>
      <ul className="gd-card-why">
        {fit.explanation.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <FitChart rows={chartRows(program, fit)} title={`Your grades against the profile of ${program.name}`} />
    </section>
  );
}

export default function ProgramPage() {
  const { code } = useParams();
  const compare = useCompare();
  // The answer for one code; a different code means the page is still loading.
  const [result, setResult] = useState({ code: null, data: null, error: '' });

  useEffect(() => {
    fetchProgramFit(code)
      .then((data) => setResult({ code, data, error: '' }))
      .catch((err) => setResult({ code, data: null, error: err.status === 404 ? 'This program is not available.' : err.message }));
  }, [code]);

  if (result.code !== code) return <Loading label="Loading the program…" />;
  const { data, error } = result;
  if (!data) {
    return (
      <div className="desk gd-page">
        <p className="alert alert-error">{error}</p>
        <Link className="btn btn-secondary" to="/student/guidance/programs">
          Browse all programs
        </Link>
      </div>
    );
  }

  const { program, fit } = data;
  const picked = compare.codes.includes(program.code);
  return (
    <div className="desk gd-page">
      <PageHead kicker={program.family?.name || 'College program'} title={program.name} icon="guidance">
        {program.description ? <p>{program.description}</p> : null}
      </PageHead>
      <div className="gd-split">
        <section className="card gd-panel">
          <h2>About this program</h2>
          <dl className="gd-facts">
            <div>
              <dt>Career overview</dt>
              <dd>{program.career_overview || 'Not written yet.'}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                {program.verified ? (
                  <>
                    {program.source_url ? (
                      <a href={program.source_url} target="_blank" rel="noopener noreferrer">
                        {program.source}
                      </a>
                    ) : (
                      program.source
                    )}{' '}
                    · verified {formatDate(program.verified_on)}
                  </>
                ) : (
                  'Being verified by the school'
                )}
              </dd>
            </div>
            <div>
              <dt>Profile</dt>
              <dd>{program.profile_validated ? `Version ${program.profile_version}, validated by experts` : 'Draft, being validated'}</dd>
            </div>
            {program.strands.length ? (
              <div>
                <dt>Usually after these strands</dt>
                <dd>{program.strands.join(', ')} (other strands are welcome)</dd>
              </div>
            ) : null}
          </dl>
          <div className="gd-actions">
            <button
              className="btn btn-secondary"
              type="button"
              aria-pressed={picked}
              disabled={!picked && compare.full}
              onClick={() => compare.toggle(program.code)}
            >
              {picked ? 'Picked to compare' : 'Add to compare'}
            </button>
            <Link className="btn btn-secondary" to="/student/guidance/programs">
              Browse all programs
            </Link>
          </div>
        </section>
        <Fit program={program} fit={fit} />
      </div>
      <CompareTray compare={compare} comparePath="/student/guidance/compare" />
    </div>
  );
}
