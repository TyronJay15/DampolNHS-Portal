import { useEffect, useState } from 'react';
import Loading from '../../../components/Loading/Loading';
import { createFamily, fetchGuidanceCatalog, saveInterestMap, updateFamily } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

// The six interest types of the O*NET Interest Profiler, in RIASEC order.
const TYPES = [
  { value: 'R', label: 'Realistic', hint: 'Hands-on work with tools, machines, plants or animals' },
  { value: 'I', label: 'Investigative', hint: 'Studying, researching and solving problems' },
  { value: 'A', label: 'Artistic', hint: 'Creating, designing and expressing ideas' },
  { value: 'S', label: 'Social', hint: 'Helping, teaching and caring for people' },
  { value: 'E', label: 'Enterprising', hint: 'Leading, persuading and managing' },
  { value: 'C', label: 'Conventional', hint: 'Organizing data, records and procedures' },
];

// Each family takes one to three interest types (catalog.save_interest_map checks the same rule).
const MAX_TYPES = 3;

const ORDER = TYPES.map((type) => type.value);
const LABELS = Object.fromEntries(TYPES.map((type) => [type.value, type.label]));

function TypeBadges({ types }) {
  if (!types.length) return <span className="gd-pill is-warn">No interest types yet</span>;
  return (
    <ul className="gd-type-badges" aria-label="Interest types">
      {types.map((letter) => (
        <li key={letter}>
          <span className="gd-type-letter" aria-hidden="true">
            {letter}
          </span>
          {LABELS[letter]}
        </li>
      ))}
    </ul>
  );
}

function TypePicker({ family, types, onChange }) {
  const full = types.length >= MAX_TYPES;
  return (
    <div className="gd-type-grid" role="group" aria-label={`Interest types for ${family.name}`}>
      {TYPES.map((type) => {
        const on = types.includes(type.value);
        return (
          <button
            key={type.value}
            type="button"
            className="gd-type"
            aria-pressed={on}
            disabled={!on && full}
            title={type.hint}
            onClick={() =>
              onChange(
                on ? types.filter((item) => item !== type.value) : [...types, type.value].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b)),
              )
            }
          >
            <span className="gd-type-letter" aria-hidden="true">
              {type.value}
            </span>
            <span className="gd-type-name">{type.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function FamilyRow({ family, editing, busy, onEdit, onChange, onCancel, onSave, onStatus }) {
  const programs = `${family.programs} program${family.programs === 1 ? '' : 's'}`;
  return (
    <li className={`gd-family-row${family.is_active ? '' : ' is-retired'}${editing ? ' is-editing' : ''}`}>
      <div className="gd-family-row-main">
        <div className="gd-family-row-name">
          <strong>{family.name}</strong>
          <span className="gd-note">
            {family.code} · {programs}
          </span>
        </div>
        {editing ? null : <TypeBadges types={family.interest_types} />}
        <div className="gd-family-row-actions">
          {editing ? null : (
            <button className="btn btn-secondary" type="button" disabled={busy} onClick={onEdit}>
              Edit types
            </button>
          )}
          <button className="btn btn-secondary" type="button" disabled={busy || editing} onClick={onStatus}>
            {family.is_active ? 'Retire' : 'Restore'}
          </button>
        </div>
      </div>

      {editing ? (
        <div className="gd-family-editor">
          <p className="gd-family-editor-count" aria-live="polite">
            {editing.length} of {MAX_TYPES} chosen{editing.length ? '' : ' · choose at least one'}
          </p>
          <TypePicker family={family} types={editing} onChange={onChange} />
          <div className="gd-actions">
            <button className="btn" type="button" disabled={busy || !editing.length} onClick={onSave}>
              {busy ? 'Saving…' : 'Save types'}
            </button>
            <button className="btn btn-secondary" type="button" disabled={busy} onClick={onCancel}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </li>
  );
}

export default function GuidanceFamiliesPage() {
  const [families, setFamilies] = useState(null);
  const [editing, setEditing] = useState(null); // { code, types } for the one family being edited
  const [form, setForm] = useState({ code: '', name: '' });
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchGuidanceCatalog()
      .then((data) => setFamilies(data.families))
      .catch((err) => setError(err.message));
  }, []);

  async function run(kind, request, done) {
    setBusy(kind);
    setError('');
    setMessage('');
    try {
      const data = await request();
      setFamilies(data.families);
      setMessage(done);
      return true;
    } catch (err) {
      setError(firstApiError(err));
      return false;
    } finally {
      setBusy('');
    }
  }

  if (!families && !error) return <Loading label="Loading families…" />;

  const groups = families
    ? [
        { key: 'active', title: 'Active families', rows: families.filter((family) => family.is_active) },
        { key: 'retired', title: 'Retired families', rows: families.filter((family) => !family.is_active) },
      ].filter((group) => group.rows.length)
    : [];

  function row(family) {
    const mine = editing?.code === family.code;
    return (
      <FamilyRow
        key={family.code}
        family={family}
        editing={mine ? editing.types : null}
        busy={Boolean(busy) || (Boolean(editing) && !mine)}
        onEdit={() => setEditing({ code: family.code, types: family.interest_types })}
        onChange={(types) => setEditing({ code: family.code, types })}
        onCancel={() => setEditing(null)}
        onSave={() =>
          run('map', () => saveInterestMap({ [family.code]: editing.types }), `Interest types saved for ${family.name}.`).then(
            (done) => done && setEditing(null),
          )
        }
        onStatus={() =>
          run('family', () => updateFamily(family.code, { name: family.name, is_active: !family.is_active }), `${family.name} saved.`)
        }
      />
    );
  }

  return (
    <>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {message ? <p className="alert alert-info">{message}</p> : null}

      <section className="card gd-panel" aria-labelledby="gd-types-title">
        <div className="gd-section-head">
          <h3 id="gd-types-title">The six interest types</h3>
          <p>Give each family the one to three types that fit it best.</p>
        </div>
        <ul className="gd-type-legend">
          {TYPES.map((type) => (
            <li key={type.value}>
              <span className="gd-type-letter" aria-hidden="true">
                {type.value}
              </span>
              <span>
                <strong>{type.label}</strong>
                <small>{type.hint}</small>
              </span>
            </li>
          ))}
        </ul>
        <p className="gd-note">
          These types set only the High, Medium or Low interest label for a family. The first map is a proposal, not a published
          crosswalk; the school panel approves or edits it here.
        </p>
      </section>

      {groups.map((group) => (
        <section key={group.key} className="card gd-panel" aria-labelledby={`gd-families-${group.key}`}>
          <div className="gd-section-head">
            <h3 id={`gd-families-${group.key}`}>{group.title}</h3>
            <p>
              {group.rows.length} famil{group.rows.length === 1 ? 'y' : 'ies'}
            </p>
          </div>
          <ul className="gd-family-list">{group.rows.map(row)}</ul>
        </section>
      ))}

      <section className="card gd-panel" aria-labelledby="gd-family-add">
        <div className="gd-section-head">
          <h3 id="gd-family-add">Add a program family</h3>
          <p>Then use Edit types to give it its interest types.</p>
        </div>
        <form
          className="gd-family-form"
          onSubmit={(event) => {
            event.preventDefault();
            run('add', () => createFamily(form), 'Family added.').then((done) => done && setForm({ code: '', name: '' }));
          }}
        >
          <label className="form-field" htmlFor="gd-family-code">
            <span>Code</span>
            <input
              id="gd-family-code"
              required
              maxLength={32}
              pattern="[a-z0-9][a-z0-9\-]{1,31}"
              title="Lowercase letters, digits or hyphens"
              placeholder="e.g. health"
              value={form.code}
              onChange={(event) => setForm({ ...form, code: event.target.value })}
            />
          </label>
          <label className="form-field" htmlFor="gd-family-name">
            <span>Name</span>
            <input
              id="gd-family-name"
              required
              maxLength={120}
              placeholder="e.g. Health and allied sciences"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
          </label>
          <button className="btn" type="submit" disabled={Boolean(busy)}>
            {busy === 'add' ? 'Adding…' : 'Add family'}
          </button>
        </form>
      </section>
    </>
  );
}
