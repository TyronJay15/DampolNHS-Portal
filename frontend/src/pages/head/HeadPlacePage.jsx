import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import AdvancedToolBanner from '../../components/AdvancedToolBanner/AdvancedToolBanner';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchPlacements, fetchSections, savePlacement, savePlacementsBulk } from '../../services/adminService';
import { isCapacityError, programChangeNote } from '../../utils/placement';
import { sectionLabel } from '../../utils/sectionLabel';

function matches(row, query) {
  if (!query) return true;
  const hay = [row.name, row.lrn, row.program_code, row.section].join(' ').toLowerCase();
  return hay.includes(query);
}

export default function HeadPlacePage() {
  const [students, setStudents] = useState([]);
  const [sections, setSections] = useState([]);
  const [sectionId, setSectionId] = useState('');
  const [sectionQuery, setSectionQuery] = useState('');
  const [studentQuery, setStudentQuery] = useState('');
  const [studentTab, setStudentTab] = useState('available');
  const [selected, setSelected] = useState({});
  const [transferTarget, setTransferTarget] = useState(null);
  const [capacityRetry, setCapacityRetry] = useState(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    const [placementRows, sectionRows] = await Promise.all([fetchPlacements(), fetchSections()]);
    setStudents(placementRows);
    setSections(sectionRows);
    setSectionId((current) => current || (sectionRows[0] ? String(sectionRows[0].id) : ''));
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const section = sections.find((row) => String(row.id) === String(sectionId));
  const filteredSections = useMemo(() => {
    const needle = sectionQuery.trim().toLowerCase();
    return sections.filter((row) => !needle || sectionLabel(row).toLowerCase().includes(needle));
  }, [sections, sectionQuery]);

  const roster = useMemo(
    () => students.filter((row) => row.section_id === Number(sectionId) && matches(row, studentQuery.trim().toLowerCase())),
    [students, sectionId, studentQuery],
  );

  // available: unplaced, same program · other: placed elsewhere (transfer) · in_section: this roster
  const pool = useMemo(() => {
    const needle = studentQuery.trim().toLowerCase();
    return students.filter((row) => {
      if (!section) return false;
      const here = row.section_id === Number(sectionId);
      if (studentTab === 'available' && row.placed) return false;
      if (studentTab === 'other' && (!row.placed || here)) return false;
      if (studentTab === 'in_section' && !here) return false;
      if (row.grade_level && section.grade_level && row.grade_level !== section.grade_level) return false;
      if (!row.placed && row.program_code && section.program_code && row.program_code !== section.program_code) return false;
      return matches(row, needle);
    });
  }, [students, studentTab, sectionId, section, studentQuery]);

  const chosen = pool.filter((row) => selected[row.student_id]);

  function retryOnCapacity(err, retry) {
    if (isCapacityError(err)) setCapacityRetry(retry);
    else setError(err.message);
  }

  async function placeBulk(force = false) {
    if (!section || chosen.length === 0) return;
    setBusy('bulk');
    setError('');
    try {
      const result = await savePlacementsBulk({
        section: Number(sectionId),
        students: chosen.map((row) => row.student_id),
        override_capacity: force,
        reason,
      });
      setSelected({});
      setCapacityRetry(null);
      await load();
      const failedNote = result.failed?.length ? ` ${result.failed.length} could not be placed.` : '';
      setMessage(`Placed ${result.placed} student(s) in ${sectionLabel(section)}.${failedNote}`);
    } catch (err) {
      retryOnCapacity(err, { type: 'bulk' });
    } finally {
      setBusy('');
    }
  }

  async function transferOne(row, force = false) {
    setBusy(`move-${row.student_id}`);
    setError('');
    try {
      await savePlacement({
        student: row.student_id,
        section: Number(sectionId),
        transfer: Boolean(row.placed),
        override_capacity: force,
        reason,
      });
      setTransferTarget(null);
      setCapacityRetry(null);
      setReason('');
      await load();
      setMessage(`${row.placed ? 'Transferred' : 'Placed'} ${row.name} in ${sectionLabel(section)}.`);
    } catch (err) {
      setTransferTarget(null);
      retryOnCapacity(err, { type: 'one', row });
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading placements…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Advanced" title="Place students" icon="place">
        <p>Pick a section, then assign or transfer students. Every change syncs with Section Management and Workspace.</p>
      </PageHead>
      <AdvancedToolBanner />
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-split-panels">
        <section className="card studio-panel">
          <label className="studio-search studio-search-wide">
            <span>Search sections</span>
            <input value={sectionQuery} onChange={(e) => setSectionQuery(e.target.value)} placeholder="Section name" />
          </label>
          <div className="studio-pick-list studio-pick-list-scroll">
            {filteredSections.map((row) => (
              <button
                key={row.id}
                type="button"
                className={`studio-pick${String(row.id) === String(sectionId) ? ' is-active' : ''}`}
                onClick={() => setSectionId(String(row.id))}
              >
                <strong>{sectionLabel(row)}</strong>
                <em>{row.student_count || 0}{row.capacity ? ` / ${row.capacity}` : ''}</em>
              </button>
            ))}
          </div>
          {section ? (
            <Link className="btn btn-secondary" to={`/head/sections/${section.id}/setup?step=students`}>
              Open in Section Workspace
            </Link>
          ) : null}
        </section>

        <section className="card studio-panel">
          <div className="studio-toolbar">
            <div>
              <h2>{section ? sectionLabel(section) : 'Select a section'}</h2>
              <p className="studio-empty">{roster.length} currently placed</p>
            </div>
            <div className="studio-filters">
              <button type="button" className={`studio-filter${studentTab === 'available' ? ' is-active' : ''}`} onClick={() => setStudentTab('available')}>Available</button>
              <button type="button" className={`studio-filter${studentTab === 'other' ? ' is-active' : ''}`} onClick={() => setStudentTab('other')}>Other sections</button>
              <button type="button" className={`studio-filter${studentTab === 'in_section' ? ' is-active' : ''}`} onClick={() => setStudentTab('in_section')}>In section</button>
            </div>
          </div>
          <label className="studio-search studio-search-wide">
            <span>Search students</span>
            <input value={studentQuery} onChange={(e) => setStudentQuery(e.target.value)} placeholder="Name or LRN" />
          </label>
          {studentTab === 'available' ? (
            <div className="studio-actions">
              <button className="btn" type="button" disabled={busy === 'bulk' || chosen.length === 0} onClick={() => placeBulk(false)}>
                {busy === 'bulk' ? 'Placing…' : `Assign selected (${chosen.length})`}
              </button>
            </div>
          ) : null}
          <div className="studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  {studentTab === 'available' ? <th /> : null}
                  <th>Student</th>
                  <th>LRN</th>
                  <th>Program</th>
                  <th>Current section</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {pool.length === 0 ? (
                  <tr>
                    <td colSpan={studentTab === 'available' ? 6 : 5}>
                      {studentTab === 'other' ? 'No students in other sections of this grade level.' : 'No students here.'}
                    </td>
                  </tr>
                ) : null}
                {pool.map((row) => (
                  <tr key={row.student_id}>
                    {studentTab === 'available' ? (
                      <td>
                        <input
                          type="checkbox"
                          checked={Boolean(selected[row.student_id])}
                          onChange={(e) => setSelected((c) => ({ ...c, [row.student_id]: e.target.checked }))}
                        />
                      </td>
                    ) : null}
                    <td>{row.name}</td>
                    <td>{row.lrn}</td>
                    <td>{row.program_code || '—'}</td>
                    <td>{row.section || '—'}</td>
                    <td>
                      {studentTab === 'other' ? (
                        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => setTransferTarget(row)}>
                          Transfer here
                        </button>
                      ) : null}
                      {studentTab === 'available' ? (
                        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => transferOne(row)}>
                          Assign
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {transferTarget ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Confirm transfer</h2>
            <p>
              Move <strong>{transferTarget.name}</strong> from <strong>{transferTarget.section || 'unplaced'}</strong> to{' '}
              <strong>{section ? sectionLabel(section) : ''}</strong>?
            </p>
            {programChangeNote(transferTarget, section) ? (
              <p className="alert alert-info">{programChangeNote(transferTarget, section)}</p>
            ) : null}
            <label className="form-field is-wide">
              <span>Reason (optional)</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setTransferTarget(null)}>Cancel</button>
              <button className="btn" type="button" onClick={() => transferOne(transferTarget)} disabled={Boolean(busy)}>Confirm transfer</button>
            </div>
          </div>
        </div>
      ) : null}

      {capacityRetry ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Section is full</h2>
            <p>
              <strong>{section ? sectionLabel(section) : ''}</strong> is at capacity ({section?.student_count || 0}
              {section?.capacity ? ` / ${section.capacity}` : ''}). Place anyway?
            </p>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setCapacityRetry(null)}>Cancel</button>
              <button
                className="btn"
                type="button"
                disabled={Boolean(busy)}
                onClick={() => (capacityRetry.type === 'bulk' ? placeBulk(true) : transferOne(capacityRetry.row, true))}
              >
                Place anyway
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
