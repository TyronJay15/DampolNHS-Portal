import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { formatDate } from '../../../components/Guidance/guidanceText';
import Icon from '../../../components/Icon/Icon';
import Loading from '../../../components/Loading/Loading';
import { activateRecommenderConfig, fetchRecommenderConfig, saveRecommenderConfig } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

// Live matcher only. Academic fit, interest and shortlist change what students see.
const GROUPS = [
  {
    key: 'academic_tiers',
    title: 'Academic fit',
    icon: 'grades',
    text: "How close a student's shown grades must be to a program's profile.",
    fields: [
      ['strong', 'Strong tier: distance at most', 'Grade points. Closer than this is a Strong academic match.', '0.1'],
      ['moderate', 'Moderate tier: distance at most', 'Above this the academic tier is Low.', '0.1'],
    ],
  },
  {
    key: 'interest_tiers',
    title: 'Interest',
    icon: 'guidance',
    text: 'How strongly the interest survey must point to a program family.',
    fields: [
      ['high', 'High interest: family score at least', 'On the 1 to 5 scale.', '0.1'],
      ['medium', 'Medium interest: family score at least', 'Below this the interest tier is Low.', '0.1'],
    ],
  },
  {
    key: 'shortlist',
    title: 'Shortlist',
    icon: 'audit',
    text: 'How many programs a student sees.',
    fields: [
      ['primary', 'Primary programs', 'Shown as the top cards.', '1'],
      ['additional', 'Additional programs (at most)', 'Fewer appear when evidence is thin.', '1'],
    ],
  },
];

const ALL_FIELDS = GROUPS.flatMap((group) => group.fields.map(([key]) => `${group.key}.${key}`));

function asForm(values) {
  return Object.fromEntries(
    ALL_FIELDS.map((name) => {
      const [group, key] = name.split('.');
      return [name, String(values[group][key])];
    }),
  );
}

function asValues(form, stored) {
  const live = {};
  ALL_FIELDS.forEach((name) => {
    const [group, key] = name.split('.');
    live[group] = { ...(live[group] || {}), [key]: Number(form[name]) };
  });
  return {
    academic_tiers: live.academic_tiers,
    interest_tiers: live.interest_tiers,
    shortlist: live.shortlist,
    readiness: stored.readiness,
    neighbors: stored.neighbors,
  };
}

export default function GuidanceSettingsPage() {
  const confirm = useConfirm();
  const [data, setData] = useState(null);
  const [form, setForm] = useState(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function show(payload) {
    setData(payload);
    const current = payload.versions.find((row) => row.active);
    setForm(asForm(current ? current.values : payload.defaults));
  }

  useEffect(() => {
    fetchRecommenderConfig()
      .then(show)
      .catch((err) => setError(err.message));
  }, []);

  function storedValues() {
    const active = data?.versions.find((row) => row.active);
    return active ? active.values : data.defaults;
  }

  async function save(event) {
    event.preventDefault();
    const answer = await confirm({
      title: 'Save and activate these settings?',
      body: 'They become a new version. Every recommendation records the version it used, so results stay explainable. The change, its reason and every changed value are audited.',
      confirmLabel: 'Save and activate',
    });
    if (!answer) return;
    setBusy(true);
    setError('');
    try {
      show(await saveRecommenderConfig({ values: asValues(form, storedValues()), note, activate: true }));
      setNote('');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function activate(row) {
    const answer = await confirm({
      title: `Activate settings v${row.version}?`,
      body: 'Recommendations made from now on use these values. The change is audited.',
      confirmLabel: 'Activate',
    });
    if (!answer) return;
    setBusy(true);
    setError('');
    try {
      show(await activateRecommenderConfig(row.id));
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!data && !error) return <Loading label="Loading settings…" />;

  const active = data?.versions.find((row) => row.active);
  const baseline = form ? asForm(active ? active.values : data.defaults) : {};
  const changed = form ? ALL_FIELDS.filter((name) => Number(form[name]) !== Number(baseline[name])) : [];

  return (
    <>
      {error ? <p className="alert alert-error">{error}</p> : null}

      {data ? (
        <section className="card gd-panel" aria-labelledby="gd-current-title">
          <div className="gd-section-head">
            <h3 id="gd-current-title">Active settings</h3>
            <div className="gd-actions">
              {active ? <span className="gd-pill is-ok">v{active.version} active</span> : <span className="gd-pill is-warn">Documented defaults</span>}
              <Link className="btn btn-secondary" to="/admin/audit?family=guidance">
                View audit trail
              </Link>
            </div>
          </div>
          <p className="gd-note">
            {active
              ? `Saved ${formatDate(active.created_at)}${active.created_by ? ` by ${active.created_by}` : ''}${active.note ? ` · “${active.note}”` : ''}`
              : 'No version has been saved yet, so the documented defaults are in use.'}
          </p>
        </section>
      ) : null}

      {form ? (
        <div className="gd-settings">
          <form className="gd-settings-main" onSubmit={save}>
            {GROUPS.map((group) => (
              <section key={group.key} className="card gd-group" aria-labelledby={`gd-group-${group.key}`}>
                <header className="gd-group-head">
                  <span className="gd-group-icon">
                    <Icon name={group.icon} size={18} />
                  </span>
                  <div>
                    <h3 id={`gd-group-${group.key}`}>{group.title}</h3>
                    <p>{group.text}</p>
                  </div>
                </header>
                <div className="gd-group-fields">
                  {group.fields.map(([key, label, help, step]) => {
                    const name = `${group.key}.${key}`;
                    const isChanged = changed.includes(name);
                    return (
                      <label key={name} className={`form-field gd-field${isChanged ? ' is-changed' : ''}`} htmlFor={`gd-cfg-${group.key}-${key}`}>
                        <span>{label}</span>
                        <input
                          id={`gd-cfg-${group.key}-${key}`}
                          type="number"
                          step={step}
                          required
                          value={form[name]}
                          onChange={(event) => setForm({ ...form, [name]: event.target.value })}
                        />
                        <small className="gd-note">
                          {isChanged ? <strong>Was {baseline[name]}. </strong> : null}
                          {help}
                        </small>
                      </label>
                    );
                  })}
                </div>
              </section>
            ))}

            <div className="gd-savebar" role="region" aria-label="Save settings">
              <p className={`gd-savebar-count${changed.length ? ' is-changed' : ''}`} aria-live="polite">
                {changed.length ? `${changed.length} value${changed.length === 1 ? '' : 's'} changed` : 'No values changed'}
              </p>
              <label className="form-field gd-savebar-note" htmlFor="gd-cfg-note">
                <span className="gd-sr">Why this change</span>
                <input
                  id="gd-cfg-note"
                  maxLength={255}
                  required
                  placeholder="Why this change (recorded in the audit log)"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </label>
              <div className="gd-actions">
                <button className="btn btn-secondary" type="button" disabled={busy || !changed.length} onClick={() => setForm(baseline)}>
                  Reset
                </button>
                <button className="btn" type="submit" disabled={busy || !changed.length}>
                  {busy ? 'Saving…' : 'Save as a new version'}
                </button>
              </div>
            </div>
          </form>

          <aside className="card gd-panel gd-history" aria-labelledby="gd-history-title">
            <h3 id="gd-history-title">Version history</h3>
            {data.versions.length ? (
              <ol className="gd-timeline">
                {data.versions.map((row) => (
                  <li key={row.id} className={row.active ? 'is-active' : undefined}>
                    <div className="gd-timeline-head">
                      <strong>v{row.version}</strong>
                      {row.active ? <span className="gd-pill is-strong">Active</span> : null}
                    </div>
                    <small>
                      {formatDate(row.created_at)}
                      {row.created_by ? ` · ${row.created_by}` : ''}
                    </small>
                    <p>{row.note || 'No reason was recorded.'}</p>
                    {row.active ? null : (
                      <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => activate(row)}>
                        Activate v{row.version}
                      </button>
                    )}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="gd-note">No version saved yet.</p>
            )}
          </aside>
        </div>
      ) : null}
    </>
  );
}
