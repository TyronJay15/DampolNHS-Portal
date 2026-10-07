import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Loading from '../../../components/Loading/Loading';
import MetricStrip from '../../../components/MetricStrip/MetricStrip';
import { createProgram, fetchGuidanceCatalog, importPrograms } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';
import { formatDate } from '../../../components/Guidance/guidanceText';

const EMPTY = { code: '', name: '', family: '' };

function ImportPanel({ onImported }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(commit) {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const result = await importPrograms(file, commit);
      setPreview(result);
      if (result.committed) onImported();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card gd-panel" aria-labelledby="gd-import-title">
      <h3 id="gd-import-title">Import from a CSV file</h3>
      <p className="gd-note">
        Columns: code, name, abbreviation, family, description, career_overview, source, source_url, verified_on (YYYY-MM-DD). Up to
        500 rows and 1 MB. New programs are added switched off; existing ones get their descriptions updated. Run the dry run first.
      </p>
      <div className="gd-actions">
        <input
          aria-label="CSV file"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setPreview(null);
          }}
        />
        <button className="btn btn-secondary" type="button" disabled={!file || busy} onClick={() => run(false)}>
          Dry run
        </button>
        <button
          className="btn"
          type="button"
          disabled={!file || busy || !preview || preview.errors > 0 || preview.committed}
          onClick={() => run(true)}
        >
          Import
        </button>
      </div>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {preview ? (
        <div className="studio-table-wrap">
          <p className={preview.errors ? 'alert alert-error' : 'alert alert-info'}>
            {preview.committed
              ? `Imported ${preview.rows.length} row(s).`
              : preview.errors
                ? `${preview.errors} row(s) need fixing before anything is imported.`
                : `${preview.rows.length} row(s) are ready to import.`}
          </p>
          <table className="studio-table gd-table">
            <thead>
              <tr>
                <th scope="col">Line</th>
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Result</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr key={row.line}>
                  <td>{row.line}</td>
                  <td>{row.code}</td>
                  <td>{row.name}</td>
                  <td>{row.errors.length ? row.errors.join(' ') : row.action === 'create' ? 'New program' : 'Update'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default function GuidanceCatalogPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [family, setFamily] = useState('');

  function load() {
    fetchGuidanceCatalog()
      .then(setData)
      .catch((err) => setError(err.message));
  }

  useEffect(load, []);

  const programs = useMemo(
    () => (data?.programs || []).filter((program) => !family || program.family?.code === family),
    [data, family],
  );

  async function add(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await createProgram(form);
      setForm(EMPTY);
      load();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!data && !error) return <Loading label="Loading the catalog…" />;

  const counts = data
    ? {
        total: data.programs.length,
        active: data.programs.filter((row) => row.is_active).length,
        verified: data.programs.filter((row) => row.verified).length,
        validated: data.programs.filter((row) => row.profile_validated).length,
      }
    : null;

  return (
    <>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {counts ? (
        <MetricStrip
          items={[
            { key: 'total', label: 'Programs in the catalog', value: counts.total, icon: 'guidance', tone: 'blue' },
            { key: 'active', label: 'Shown to students', value: counts.active, icon: 'check', tone: 'green' },
            { key: 'verified', label: 'Verified source', value: counts.verified, icon: 'approve', tone: 'purple' },
            { key: 'validated', label: 'Profiles validated', value: counts.validated, icon: 'grades', tone: 'gold' },
          ]}
        />
      ) : null}

      {data ? (
        <section className="card studio-table-wrap" aria-label="Programs">
          <div className="gd-panel">
            <div className="gd-section-head">
              <h3>Programs</h3>
              <span className="gd-note">
                {programs.length} of {counts.total} shown
              </span>
            </div>
            <div className="gd-chips" role="group" aria-label="Filter by program family">
              {[{ code: '', name: 'All families' }, ...data.families].map((row) => (
                <button key={row.code || 'all'} type="button" className="gd-chip" aria-pressed={family === row.code} onClick={() => setFamily(row.code)}>
                  {row.name}
                  <span>{row.code ? data.programs.filter((program) => program.family?.code === row.code).length : counts.total}</span>
                </button>
              ))}
            </div>
          </div>
          <table className="studio-table gd-table">
            <thead>
              <tr>
                <th scope="col">Program</th>
                <th scope="col">Family</th>
                <th scope="col">Source</th>
                <th scope="col">Profile</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="gd-sr">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {programs.map((program) => (
                <tr key={program.code}>
                  <td>
                    <strong>{program.name}</strong>
                    <br />
                    <span className="gd-note">{program.code}</span>
                  </td>
                  <td>{program.family?.name || '—'}</td>
                  <td>
                    {program.verified ? (
                      <span className="gd-pill is-ok">Verified {formatDate(program.verified_on)}</span>
                    ) : (
                      <span className="gd-pill is-warn">Not verified</span>
                    )}
                  </td>
                  <td>
                    {program.profile_validated ? (
                      <span className="gd-pill is-ok">v{program.profile_version} validated</span>
                    ) : (
                      <span className="gd-pill is-warn">Draft</span>
                    )}
                  </td>
                  <td>
                    <span className={`gd-pill${program.is_active ? ' is-strong' : ''}`}>{program.is_active ? 'Active' : 'Off'}</span>
                  </td>
                  <td>
                    <Link className="btn btn-secondary" to={`/admin/guidance/programs/${program.code}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {data ? (
        <div className="gd-split">
          <section className="card gd-panel" aria-labelledby="gd-add-title">
            <h3 id="gd-add-title">Add a program</h3>
            <p className="gd-note">Use the official program name. A new program stays off until it is verified and its profile is validated.</p>
            <form onSubmit={add}>
              <div className="gd-form-grid">
                <label className="form-field" htmlFor="gd-new-code">
                  <span>Code</span>
                  <input
                    id="gd-new-code"
                    required
                    maxLength={32}
                    pattern="[a-z0-9][a-z0-9\-]{1,31}"
                    title="Lowercase letters, digits or hyphens"
                    value={form.code}
                    onChange={(event) => setForm({ ...form, code: event.target.value })}
                  />
                </label>
                <label className="form-field" htmlFor="gd-new-family">
                  <span>Family</span>
                  <select id="gd-new-family" required value={form.family} onChange={(event) => setForm({ ...form, family: event.target.value })}>
                    <option value="">Choose a family</option>
                    {data.families.map((row) => (
                      <option key={row.code} value={row.code}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-field is-wide" htmlFor="gd-new-name">
                  <span>Official name</span>
                  <input id="gd-new-name" required maxLength={160} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
                </label>
              </div>
              <button className="btn" type="submit" disabled={busy}>
                {busy ? 'Adding…' : 'Add program'}
              </button>
            </form>
          </section>
          <ImportPanel onImported={load} />
        </div>
      ) : null}
    </>
  );
}
