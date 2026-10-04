import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useProposal } from '../../components/Access/proposalContext';
import AdvancedToolBanner from '../../components/AdvancedToolBanner/AdvancedToolBanner';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchPlacements, fetchSections, savePlacement, savePlacementsBulk } from '../../services/adminService';
import { isCapacityError, programChangeNote } from '../../utils/placement';
import { sectionLabel } from '../../utils/sectionLabel';
import { genderLabel } from '../../utils/gender';

function matches(row, query) {
  if (!query) return true;
  const hay = [row.name, row.lrn, row.program_code, row.section].join(' ').toLowerCase();
  return hay.includes(query);
}

export default function HeadPlacePage() {
  const confirm = useConfirm();
  // Set when a teacher tagged to prepare placements opens this page: placements become requests.
  const proposal = useProposal();
  const [students, setStudents] = useState([]);
  const [sections, setSections] = useState([]);
  const [sectionId, setSectionId] = useState('');
  const [sectionQuery, setSectionQuery] = useState('');
  const [studentQuery, setStudentQuery] = useState('');
  const [studentTab, setStudentTab] = useState('available');
  const [selected, setSelected] = useState({});
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

  const reasonNote = { label: 'Reason', placeholder: 'Why is this change being made?' };

  // Asked when the server reports the section is full; returns the reason, or null if declined.
  async function confirmOverCapacity(reason) {
    const answer = await confirm({
      title: 'Section is full',
      body: `${sectionLabel(section)} is at capacity (${section?.student_count || 0}${section?.capacity ? ` / ${section.capacity}` : ''}). Place anyway?`,
      confirmLabel: 'Place anyway',
      tone: 'warning',
      note: { label: 'Reason', placeholder: 'Why exceed capacity?', required: true, initial: reason },
    });
    return answer ? answer.note : null;
  }

  // Runs a placement request; if the section is full, asks once and retries with the override.
  async function submitPlacement(key, send, reason, onDone) {
    let note = reason;
    let force = false;
    for (;;) {
      setBusy(key);
      setError('');
      try {
        await send(force, note);
        await load();
        onDone();
        return;
      } catch (err) {
        if (force || !isCapacityError(err)) {
          setError(err.message);
          return;
        }
        setBusy('');
        note = await confirmOverCapacity(note);
        if (note === null) return;
        force = true;
      } finally {
        setBusy('');
      }
    }
  }

  async function proposePlacement(rows, transfer) {
    setError('');
    try {
      const sent = await proposal.propose(
        { section: Number(sectionId), students: rows.map((row) => row.student_id), transfer },
        {
          title: `Propose ${transfer ? 'transferring' : 'placing'} ${rows.length === 1 ? rows[0].name : `${rows.length} students`}?`,
          facts: [
            { label: 'Section', value: sectionLabel(section) },
            { label: 'Students', value: rows.length },
          ],
          warning: transfer ? programChangeNote(rows[0], section) || undefined : undefined,
        },
      );
      if (!sent) return;
      setSelected({});
      setMessage('Sent to the Head Teacher for approval. Follow it under My access.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function placeBulk() {
    if (!section || chosen.length === 0) return;
    if (proposal) return proposePlacement(chosen, false);
    const answer = await confirm({
      title: `Assign ${chosen.length} student${chosen.length === 1 ? '' : 's'}?`,
      body: `They are placed in ${sectionLabel(section)} and appear on its roster.`,
      confirmLabel: 'Assign students',
      facts: [
        { label: 'Selected', value: chosen.length },
        { label: 'Placed now', value: section.student_count || 0 },
      ],
      note: reasonNote,
    });
    if (!answer) return;
    await submitPlacement(
      'bulk',
      async (force, note) => {
        const result = await savePlacementsBulk({
          section: Number(sectionId),
          students: chosen.map((row) => row.student_id),
          override_capacity: force,
          reason: note,
        });
        const failedNote = result.failed?.length ? ` ${result.failed.length} could not be placed.` : '';
        setSelected({});
        setMessage(`Placed ${result.placed} student(s) in ${sectionLabel(section)}.${failedNote}`);
      },
      answer.note,
      () => {},
    );
  }

  async function transferOne(row) {
    const moving = Boolean(row.placed);
    if (proposal) return proposePlacement([row], moving);
    let reason = '';
    // Placing an unplaced student is routine; moving one between sections asks first.
    if (moving) {
      const answer = await confirm({
        title: `Transfer ${row.name}?`,
        body: `Move from ${row.section || 'unplaced'} to ${sectionLabel(section)}.`,
        confirmLabel: 'Transfer',
        warning: programChangeNote(row, section) || undefined,
        note: reasonNote,
      });
      if (!answer) return;
      reason = answer.note;
    }
    await submitPlacement(
      `move-${row.student_id}`,
      (force, note) =>
        savePlacement({
          student: row.student_id,
          section: Number(sectionId),
          transfer: moving,
          override_capacity: force,
          reason: note,
        }),
      reason,
      () => setMessage(`${moving ? 'Transferred' : 'Placed'} ${row.name} in ${sectionLabel(section)}.`),
    );
  }

  if (loading) return <Loading label="Loading placements…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Advanced" title="Place students" icon="place">
        <p>Pick a section, then assign or transfer students. Every change syncs with Section Management and Workspace.</p>
      </PageHead>
      {proposal ? null : <AdvancedToolBanner />}
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
          {section && !proposal ? (
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
              <button className="btn" type="button" disabled={busy === 'bulk' || chosen.length === 0} onClick={placeBulk}>
                {busy === 'bulk' ? 'Placing…' : `${proposal ? 'Propose assigning' : 'Assign selected'} (${chosen.length})`}
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
                    <td>
                      {row.name}
                      {row.gender ? <p className="studio-table-sub">{genderLabel(row.gender)}</p> : null}
                    </td>
                    <td>{row.lrn}</td>
                    <td>{row.program_code || '—'}</td>
                    <td>{row.section || '—'}</td>
                    <td>
                      {studentTab === 'other' ? (
                        <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={() => transferOne(row)}>
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
    </div>
  );
}
