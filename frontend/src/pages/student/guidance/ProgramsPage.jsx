import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import CompareTray from '../../../components/Guidance/CompareTray';
import useCompare from '../../../components/Guidance/useCompare';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import { fetchCatalog } from '../../../services/guidanceService';
import '../../../components/Guidance/Guidance.css';

// Every active program, recommended or not, so the shortlist never hides an alternative.
export default function ProgramsPage() {
  const compare = useCompare();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [family, setFamily] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetchCatalog()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  const programs = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (data?.programs || []).filter(
      (program) =>
        (!family || program.family?.code === family) &&
        (!text || `${program.name} ${program.abbreviation}`.toLowerCase().includes(text)),
    );
  }, [data, family, query]);

  if (!data && !error) return <Loading label="Loading programs…" />;

  return (
    <div className="desk gd-page">
      <PageHead kicker="College recommendation" title="Browse all programs" icon="guidance">
        <p>Open any program to see how your own grades and interests relate to it. Pick up to three to compare.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {data ? (
        <>
          <div className="card gd-panel">
            <div className="studio-toolbar">
              <label className="form-field" htmlFor="gd-family">
                <span>Program family</span>
                <select id="gd-family" value={family} onChange={(event) => setFamily(event.target.value)}>
                  <option value="">All families</option>
                  {data.families.map((row) => (
                    <option key={row.code} value={row.code}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field" htmlFor="gd-search">
                <span>Search</span>
                <input
                  id="gd-search"
                  type="search"
                  value={query}
                  placeholder="Program name"
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
            </div>
            <p className="gd-note">
              {programs.length} of {data.programs.length} programs
            </p>
          </div>
          {programs.length ? (
            <div className="gd-explore">
              {programs.map((program) => {
                const picked = compare.codes.includes(program.code);
                return (
                  <article key={program.code} className="gd-mini">
                    <strong>{program.name}</strong>
                    <small>{program.family?.name}</small>
                    {program.description ? <small>{program.description}</small> : null}
                    {program.profile_validated ? null : <small>Profile being validated by teachers.</small>}
                    <div className="gd-actions">
                      <Link className="btn btn-secondary" to={`/student/guidance/programs/${program.code}`}>
                        View program
                      </Link>
                      <button
                        className="btn btn-secondary"
                        type="button"
                        aria-pressed={picked}
                        disabled={!picked && compare.full}
                        onClick={() => compare.toggle(program.code)}
                      >
                        {picked ? 'Picked' : 'Compare'}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="card gd-panel gd-note">No program matches this filter.</p>
          )}
        </>
      ) : null}
      <Link className="btn btn-secondary" to="/student/guidance">
        Back to my matches
      </Link>
      <CompareTray compare={compare} comparePath="/student/guidance/compare" />
    </div>
  );
}
