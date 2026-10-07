import { useEffect, useMemo, useState } from 'react';
import { useProposal } from '../../components/Access/proposalContext';
import Loading from '../../components/Loading/Loading';
import { fetchRatingForm } from '../../services/guidanceService';
import { firstApiError } from '../../utils/authRules';
import '../../components/Guidance/Guidance.css';

function emptyRows(domains, mine) {
  const saved = Object.fromEntries(mine.map((row) => [row.domain, row]));
  return Object.fromEntries(
    domains.map((domain) => [
      domain.key,
      { importance: saved[domain.key]?.importance || '', benchmark: saved[domain.key]?.benchmark ?? '' },
    ]),
  );
}

// Expert validation: rate how important each skill area is for this program, relative to a typical
// Grade 12 graduate. Every skill area is required. The Admin applies the median of several experts.
export default function ProgramRatingsWork() {
  const proposal = useProposal();
  const [form, setForm] = useState(null);
  const [code, setCode] = useState('');
  const [rows, setRows] = useState({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchRatingForm()
      .then(setForm)
      .catch((err) => setError(err.message));
  }, []);

  const program = useMemo(() => form?.programs.find((row) => row.code === code), [form, code]);
  const choices = form?.importance || [];

  function choose(nextCode) {
    setCode(nextCode);
    setMessage('');
    const next = form.programs.find((row) => row.code === nextCode);
    setRows(next ? emptyRows(form.domains, next.mine) : {});
  }

  function update(domain, field, value) {
    setRows((current) => ({ ...current, [domain]: { ...current[domain], [field]: value } }));
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    const missing = form.domains.filter((domain) => !rows[domain.key]?.importance);
    if (missing.length) {
      setError(`Rate every skill area. Still needed: ${missing.map((row) => row.label).join(', ')}.`);
      return;
    }
    const ratings = form.domains.map((domain) => ({
      domain: domain.key,
      importance: rows[domain.key].importance,
      benchmark: rows[domain.key].benchmark === '' ? null : Number(rows[domain.key].benchmark),
    }));
    try {
      const sent = await proposal.propose(
        { program: program.code, ratings },
        {
          title: `Send your ratings for ${program.name}?`,
          facts: ratings.map((row) => ({
            label: form.domains.find((domain) => domain.key === row.domain).label,
            value: choices.find((choice) => choice.key === row.importance)?.label || row.importance,
          })),
        },
      );
      if (sent) setMessage('Sent to the Admin for approval.');
    } catch (err) {
      setError(firstApiError(err));
    }
  }

  if (!form && !error) return <Loading label="Loading programs…" />;

  return (
    <div className="desk">
      {error ? <p className="alert alert-error">{error}</p> : null}
      {message ? <p className="alert alert-info">{message}</p> : null}
      {form ? (
        <section className="card gd-panel">
          <h2>Rate a college program profile</h2>
          <p className="gd-note">
            For each skill area, say how important it is for this program compared with a typical Grade 12 graduate. Do
            not give every area the top rating. The Admin needs ratings from at least {form.min_raters} experts, and
            Apply is blocked if experts still disagree by 12 points or more.
          </p>
          <label className="form-field" htmlFor="rate-program">
            <span>Program</span>
            <select id="rate-program" value={code} onChange={(event) => choose(event.target.value)}>
              <option value="">Choose a program</option>
              {form.programs.map((row) => (
                <option key={row.code} value={row.code}>
                  {row.name}
                  {row.family ? ` · ${row.family}` : ''}
                </option>
              ))}
            </select>
          </label>
          {program ? (
            <form className="desk gd-rate-form" onSubmit={submit}>
              {program.description ? <p className="gd-note">{program.description}</p> : null}
              {program.source ? (
                <p className="gd-note">
                  Source:{' '}
                  {program.source_url ? (
                    <a href={program.source_url} target="_blank" rel="noopener noreferrer">
                      {program.source}
                    </a>
                  ) : (
                    program.source
                  )}
                </p>
              ) : null}
              <ol className="gd-rate-list">
                {form.domains.map((domain) => (
                  <li key={domain.key}>
                    <fieldset className="gd-rate-item">
                      <legend>{domain.label}</legend>
                      <div className="gd-rate-choices">
                        {choices.map((choice) => (
                          <label key={choice.key} className={rows[domain.key]?.importance === choice.key ? 'is-picked' : ''}>
                            <input
                              type="radio"
                              name={`importance-${domain.key}`}
                              value={choice.key}
                              checked={rows[domain.key]?.importance === choice.key}
                              onChange={() => update(domain.key, 'importance', choice.key)}
                            />
                            {choice.label}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  </li>
                ))}
              </ol>
              <div className="gd-actions">
                <button className="btn" type="submit">
                  Send for approval
                </button>
                <span className="gd-note">Profile round {program.round}</span>
              </div>
            </form>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
