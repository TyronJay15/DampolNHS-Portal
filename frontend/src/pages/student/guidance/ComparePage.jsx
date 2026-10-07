import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import MatchLabel from '../../../components/Guidance/MatchLabel';
import { INTEREST_WORDS, grade } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import PageHead from '../../../components/PageHead/PageHead';
import { fetchComparison } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';
import '../../../components/Guidance/Guidance.css';

const TIERS = { strong: 'Strong', moderate: 'Moderate', low: 'Low' };

function cell(fit, render) {
  return fit.status === 'evaluated' ? render(fit) : 'Not checked yet';
}

const ROWS = [
  ['Program family', (row) => row.program.family?.name || '—'],
  ['Match', (row) => cell(row.fit, (fit) => <MatchLabel label={fit.label} />)],
  ['Academic alignment', (row) => cell(row.fit, (fit) => TIERS[fit.evidence.academic.tier])],
  ['Interest alignment', (row) => cell(row.fit, (fit) => (fit.evidence.interest ? INTEREST_WORDS[fit.evidence.interest.tier] : 'Not assessed'))],
  [
    'Relevant strengths',
    (row) =>
      cell(row.fit, (fit) =>
        fit.evidence.strengths
          .slice(0, 2)
          .map((item) => `${item.label} ${grade(item.student)}`)
          .join(', ') || '—',
      ),
  ],
  ['Description', (row) => row.program.description || '—'],
  ['Career overview', (row) => row.program.career_overview || '—'],
  ['Why', (row) => cell(row.fit, (fit) => fit.explanation[0] || '—')],
];

export default function ComparePage() {
  const [params] = useSearchParams();
  const codes = (params.get('programs') || '').split(',').filter(Boolean);
  const key = codes.join(',');
  // The answer for one set of codes; a different set means the page is still loading.
  const [result, setResult] = useState({ key: null, data: null, error: '' });

  useEffect(() => {
    fetchComparison(key.split(','))
      .then((data) => setResult({ key, data, error: '' }))
      .catch((err) => setResult({ key, data: null, error: firstApiError(err) }));
  }, [key]);

  const loading = result.key !== key;
  const { data, error } = loading ? { data: null, error: '' } : result;

  return (
    <div className="desk gd-page">
      <PageHead kicker="College recommendation" title="Compare programs" icon="guidance">
        <p>Every cell comes from the program record and your own evidence. No salary or job predictions are shown.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {loading ? <Loading label="Comparing…" /> : null}
      {data ? (
        <div className="card studio-table-wrap">
          <table className="studio-table gd-table">
            <thead>
              <tr>
                <th scope="col">
                  <span className="gd-sr">Detail</span>
                </th>
                {data.programs.map((row) => (
                  <th key={row.program.code} scope="col">
                    <Link to={`/student/guidance/programs/${row.program.code}`}>{row.program.name}</Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([label, render]) => (
                <tr key={label}>
                  <th scope="row">{label}</th>
                  {data.programs.map((row) => (
                    <td key={row.program.code}>{render(row)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <div className="gd-actions">
        <Link className="btn btn-secondary" to="/student/guidance/programs">
          Browse all programs
        </Link>
        <Link className="btn btn-secondary" to="/student/guidance">
          Back to my matches
        </Link>
      </div>
    </div>
  );
}
