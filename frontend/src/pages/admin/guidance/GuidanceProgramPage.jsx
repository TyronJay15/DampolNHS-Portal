import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { formatDate, grade } from '../../../components/Guidance/guidanceText';
import Loading from '../../../components/Loading/Loading';
import { fetchPrograms } from '../../../services/adminService';
import { fetchAdminProgram, fetchGuidanceCatalog, programAction, updateProgram } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

const DETAIL_FIELDS = ['name', 'abbreviation', 'family', 'description', 'career_overview', 'shs_programs'];

function detailsOf(program) {
  return {
    name: program.name,
    abbreviation: program.abbreviation,
    family: program.family?.code || '',
    description: program.description,
    career_overview: program.career_overview,
    shs_programs: program.shs_programs,
  };
}

export default function GuidanceProgramPage() {
  const { code } = useParams();
  const confirm = useConfirm();
  const [data, setData] = useState(null);
  const [families, setFamilies] = useState([]);
  const [shsPrograms, setShsPrograms] = useState([]);
  const [details, setDetails] = useState(null);
  const [source, setSource] = useState({ source: '', source_url: '', verified_on: '' });
  const [requirement, setRequirement] = useState({ domain: '', minimum: '', source: '' });
  const [apply, setApply] = useState({ source: '', note: '' });
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  function show(payload) {
    setData(payload);
    setDetails(detailsOf(payload.program));
    setSource({
      source: payload.program.source,
      source_url: payload.program.source_url,
      verified_on: payload.program.verified_on || '',
    });
  }

  useEffect(() => {
    Promise.all([fetchAdminProgram(code), fetchGuidanceCatalog(), fetchPrograms()])
      .then(([payload, catalog, shs]) => {
        show(payload);
        setFamilies(catalog.families);
        setShsPrograms(shs);
      })
      .catch((err) => setError(err.status === 404 ? 'This program does not exist.' : err.message));
  }, [code]);

  async function run(kind, request, done) {
    setBusy(kind);
    setError('');
    setMessage('');
    try {
      show(await request());
      if (done) setMessage(done);
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy('');
    }
  }

  if (!data && !error) return <Loading label="Loading the program…" />;
  if (!data) return <p className="alert alert-error">{error}</p>;

  const { program, ratings, snapshots } = data;

  async function toggleActive() {
    const next = !program.is_active;
    const answer = await confirm({
      title: next ? `Show ${program.name} to students?` : `Stop showing ${program.name}?`,
      body: next
        ? 'It needs a verified source and an expert-validated profile. Students can then be recommended this program.'
        : 'It disappears from recommendations and from the catalog students browse. Saved history is kept.',
      confirmLabel: next ? 'Switch on' : 'Switch off',
    });
    if (answer) await run('active', () => updateProgram(code, { is_active: next }), next ? 'Program switched on.' : 'Program switched off.');
  }

  async function applyRatings(event) {
    event.preventDefault();
    const answer = await confirm({
      title: `Apply the expert median to ${program.name}?`,
      body: `Profile version ${ratings.round} replaces the current profile. The previous version stays in the history.`,
      confirmLabel: 'Apply ratings',
      facts: ratings.areas.map((area) => ({ label: area.label, value: area.median })),
    });
    if (answer) await run('apply', () => programAction(code, 'apply-ratings', apply), 'Profile validated and saved as a new version.');
  }

  const toggleShs = (value) =>
    setDetails((current) => ({
      ...current,
      shs_programs: current.shs_programs.includes(value)
        ? current.shs_programs.filter((item) => item !== value)
        : [...current.shs_programs, value],
    }));

  return (
    <>
      <div className="studio-actions">
        <Link to="/admin/guidance">Back to programs</Link>
      </div>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {message ? <p className="alert alert-info">{message}</p> : null}

      <section className="card gd-panel">
        <div className="gd-section-head">
          <h3>{program.name}</h3>
          <div className="gd-actions">
            <span className={`gd-pill${program.is_active ? ' is-strong' : ''}`}>{program.is_active ? 'Shown to students' : 'Off'}</span>
            <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={toggleActive}>
              {program.is_active ? 'Switch off' : 'Switch on'}
            </button>
          </div>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const changes = Object.fromEntries(DETAIL_FIELDS.map((field) => [field, details[field]]));
            run('details', () => updateProgram(code, changes), 'Details saved.');
          }}
        >
          <div className="gd-form-grid">
            <label className="form-field" htmlFor="gd-p-name">
              <span>Official name</span>
              <input id="gd-p-name" required maxLength={160} value={details.name} onChange={(event) => setDetails({ ...details, name: event.target.value })} />
            </label>
            <label className="form-field" htmlFor="gd-p-abbr">
              <span>Abbreviation</span>
              <input id="gd-p-abbr" maxLength={24} value={details.abbreviation} onChange={(event) => setDetails({ ...details, abbreviation: event.target.value })} />
            </label>
            <label className="form-field" htmlFor="gd-p-family">
              <span>Family</span>
              <select id="gd-p-family" required value={details.family} onChange={(event) => setDetails({ ...details, family: event.target.value })}>
                {families.map((row) => (
                  <option key={row.code} value={row.code}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field is-wide" htmlFor="gd-p-desc">
              <span>Description</span>
              <textarea id="gd-p-desc" maxLength={4000} value={details.description} onChange={(event) => setDetails({ ...details, description: event.target.value })} />
            </label>
            <label className="form-field is-wide" htmlFor="gd-p-career">
              <span>Career overview</span>
              <textarea id="gd-p-career" maxLength={4000} value={details.career_overview} onChange={(event) => setDetails({ ...details, career_overview: event.target.value })} />
            </label>
            <fieldset className="form-field is-wide">
              <legend>Usually after these SHS programs (context only, never a restriction)</legend>
              <div className="gd-actions">
                {shsPrograms.map((row) => (
                  <label key={row.code} className="gd-check" htmlFor={`gd-shs-${row.code}`}>
                    <input id={`gd-shs-${row.code}`} type="checkbox" checked={details.shs_programs.includes(row.code)} onChange={() => toggleShs(row.code)} />
                    <span>{row.code}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
          <button className="btn" type="submit" disabled={busy === 'details'}>
            {busy === 'details' ? 'Saving…' : 'Save details'}
          </button>
        </form>
      </section>

      <div className="gd-split">
        <section className="card gd-panel" aria-labelledby="gd-source-title">
          <h3 id="gd-source-title">Authoritative source</h3>
          <p className="gd-note">
            {program.verified
              ? `Verified ${formatDate(program.verified_on)}${program.verified_by ? ` by ${program.verified_by}` : ''}.`
              : 'Not verified. Name the CHED issuance or official catalog the program comes from.'}
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              run('verify', () => programAction(code, 'verify', source), 'Source verified.');
            }}
          >
            <label className="form-field" htmlFor="gd-src">
              <span>Source</span>
              <input id="gd-src" required maxLength={255} value={source.source} onChange={(event) => setSource({ ...source, source: event.target.value })} />
            </label>
            <label className="form-field" htmlFor="gd-src-url">
              <span>Source link (optional)</span>
              <input id="gd-src-url" type="url" maxLength={200} value={source.source_url} onChange={(event) => setSource({ ...source, source_url: event.target.value })} />
            </label>
            <label className="form-field" htmlFor="gd-src-date">
              <span>Checked on</span>
              <input id="gd-src-date" type="date" required value={source.verified_on} onChange={(event) => setSource({ ...source, verified_on: event.target.value })} />
            </label>
            <button className="btn btn-secondary" type="submit" disabled={busy === 'verify'}>
              {busy === 'verify' ? 'Saving…' : 'Save as verified'}
            </button>
          </form>
        </section>

        <section className="card gd-panel" aria-labelledby="gd-profile-title">
          <h3 id="gd-profile-title">
            Profile {program.profile_validated ? `v${program.profile_version}, validated` : '(draft)'}
          </h3>
          <div className="studio-table-wrap">
            <table className="studio-table gd-table">
              <thead>
                <tr>
                  <th scope="col">Skill area</th>
                  <th scope="col">Level</th>
                  <th scope="col">Benchmark</th>
                </tr>
              </thead>
              <tbody>
                {program.profile.map((row) => (
                  <tr key={row.domain}>
                    <th scope="row">{row.label}</th>
                    <td>{grade(row.level)}</td>
                    <td>
                      {row.benchmark === null ? '—' : grade(row.benchmark)}
                      {row.official ? <span className="gd-pill is-warn"> Official · {row.requirement_source}</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form
            className="gd-form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              run(
                'requirement',
                () => programAction(code, 'requirement', { ...requirement, official: true, minimum: Number(requirement.minimum) }),
                'Official requirement saved.',
              );
            }}
          >
            <label className="form-field" htmlFor="gd-req-domain">
              <span>Official requirement in</span>
              <select id="gd-req-domain" required value={requirement.domain} onChange={(event) => setRequirement({ ...requirement, domain: event.target.value })}>
                <option value="">Choose a skill area</option>
                {program.profile.map((row) => (
                  <option key={row.domain} value={row.domain}>
                    {row.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field" htmlFor="gd-req-min">
              <span>Minimum grade</span>
              <input id="gd-req-min" type="number" min="0" max="100" required value={requirement.minimum} onChange={(event) => setRequirement({ ...requirement, minimum: event.target.value })} />
            </label>
            <label className="form-field is-wide" htmlFor="gd-req-src">
              <span>Documented source (required)</span>
              <input id="gd-req-src" required maxLength={255} value={requirement.source} onChange={(event) => setRequirement({ ...requirement, source: event.target.value })} />
            </label>
            <div className="gd-actions is-wide">
              <button className="btn btn-secondary" type="submit" disabled={busy === 'requirement'}>
                Save official requirement
              </button>
              {requirement.domain && program.profile.find((row) => row.domain === requirement.domain)?.official ? (
                <button
                  className="btn btn-secondary"
                  type="button"
                  onClick={() => run('requirement', () => programAction(code, 'requirement', { domain: requirement.domain, official: false }), 'Turned back into a benchmark.')}
                >
                  Make it a benchmark again
                </button>
              ) : null}
            </div>
          </form>
        </section>
      </div>

      <section className="card gd-panel" aria-labelledby="gd-ratings-title">
        <div className="gd-section-head">
          <h3 id="gd-ratings-title">Expert ratings for profile version {ratings.round}</h3>
          <p>
            {ratings.raters.length} expert(s) so far · at least {ratings.min_raters} needed in every skill area. Apply is
            blocked while experts disagree by {ratings.disagreement_points || 12} points or more, or if the profile is
            flat or a copy of another program.
          </p>
        </div>
        {ratings.areas.length ? (
          <div className="studio-table-wrap">
            <table className="studio-table gd-table">
              <thead>
                <tr>
                  <th scope="col">Skill area</th>
                  <th scope="col">Raters</th>
                  <th scope="col">Ratings</th>
                  <th scope="col">Median</th>
                  <th scope="col">Benchmark median</th>
                </tr>
              </thead>
              <tbody>
                {ratings.areas.map((area) => (
                  <tr key={area.domain}>
                    <th scope="row">{area.label}</th>
                    <td>{area.raters}</td>
                    <td>
                      {(area.importance?.length ? area.importance : area.levels).join(', ') || '—'}
                      {area.disagree ? <span className="gd-pill is-warn"> Discuss: wide spread</span> : null}
                    </td>
                    <td>{area.median_importance || grade(area.median)}</td>
                    <td>{area.benchmark_median ? grade(area.benchmark_median) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="gd-note">No approved ratings in this round yet.</p>
        )}
        {ratings.blockers?.length ? (
          <ul className="gd-checks">
            {ratings.blockers.map((blocker) => (
              <li key={blocker.code} className="is-no">
                {blocker.detail}
              </li>
            ))}
          </ul>
        ) : null}
        <form className="gd-form-grid" onSubmit={applyRatings}>
          <label className="form-field" htmlFor="gd-apply-src">
            <span>Official information the experts used</span>
            <input id="gd-apply-src" required maxLength={255} value={apply.source} onChange={(event) => setApply({ ...apply, source: event.target.value })} />
          </label>
          <label className="form-field" htmlFor="gd-apply-note">
            <span>Note (optional)</span>
            <input id="gd-apply-note" maxLength={255} value={apply.note} onChange={(event) => setApply({ ...apply, note: event.target.value })} />
          </label>
          <div className="gd-actions is-wide">
            <button className="btn" type="submit" disabled={!ratings.ready || busy === 'apply'}>
              Apply the median as the validated profile
            </button>
          </div>
        </form>
      </section>

      <section className="card gd-panel" aria-labelledby="gd-history-title">
        <h3 id="gd-history-title">Profile history</h3>
        <ul className="gd-card-why">
          {snapshots.map((row) => (
            <li key={row.version}>
              v{row.version} · {row.status === 'validated' ? 'validated' : 'draft'} · {formatDate(row.created_at)} · {row.raters} rater(s) ·{' '}
              {row.note || row.source}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
