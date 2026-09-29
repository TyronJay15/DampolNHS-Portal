import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import ConfirmDeleteModal from '../../components/ConfirmDeleteModal/ConfirmDeleteModal';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  fetchArchive,
  purgeDuty,
  purgeSchoolYear,
  purgeSection,
  restoreAssignment,
  restoreSchoolYear,
  restoreSection,
} from '../../services/adminService';
import { sectionLabel } from '../../utils/sectionLabel';
import { when } from '../../utils/when';

const TABS = [
  { id: 'years', label: 'Years' },
  { id: 'sections', label: 'Sections' },
  { id: 'duties', label: 'Duties' },
];

export default function HeadArchivePage() {
  const [tab, setTab] = useState('years');
  const [rows, setRows] = useState([]);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [dutyDeleteTarget, setDutyDeleteTarget] = useState(null);
  const [hardMode, setHardMode] = useState(false);
  const [confirmValue, setConfirmValue] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load(kind = tab) {
    const data = await fetchArchive(kind);
    setRows(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    load('years')
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function switchTab(next) {
    setTab(next);
    setLoading(true);
    setError('');
    try {
      await load(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function openDelete(row) {
    setDeleteTarget(row);
    setHardMode(false);
    setConfirmValue('');
    setReason('');
  }

  async function submitDelete() {
    if (!deleteTarget) return;
    if (hardMode && !reason.trim()) {
      setError('Provide a reason for hard delete.');
      return;
    }
    setBusy('delete');
    setError('');
    try {
      const payload = { hard: hardMode, confirm: confirmValue, reason: reason.trim() };
      if (tab === 'sections') {
        await purgeSection(deleteTarget.id, payload);
      } else if (tab === 'years') {
        await purgeSchoolYear(deleteTarget.id, payload);
      }
      setMessage('Deleted permanently.');
      setDeleteTarget(null);
      setHardMode(false);
      await load(tab);
    } catch (err) {
      if (err.message.includes('grade records') && !hardMode) {
        setHardMode(true);
        setError('');
      } else {
        setError(err.message);
      }
    } finally {
      setBusy('');
    }
  }

  async function submitDutyDelete() {
    if (!dutyDeleteTarget) return;
    setBusy('duty-delete');
    setError('');
    try {
      await purgeDuty(dutyDeleteTarget.id);
      setMessage('Duty deleted permanently.');
      setDutyDeleteTarget(null);
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function restore(row) {
    setBusy(String(row.id));
    setError('');
    setMessage('');
    try {
      if (tab === 'years') {
        const saved = await restoreSchoolYear(row.id);
        setMessage(`${saved.label} restored with its sections and duties where slots are free.`);
      } else if (tab === 'sections') {
        const saved = await restoreSection(row.id);
        setMessage(`${saved.display_label} restored. Check Section Management.`);
      } else {
        await restoreAssignment(row.id);
        setMessage(`${row.teacher} duty restored.`);
      }
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading archive…" />;

  const deleteLabel = tab === 'years' ? deleteTarget?.label : deleteTarget ? sectionLabel(deleteTarget) : '';
  const confirmHint =
    tab === 'years'
      ? `Type ${deleteTarget?.label || 'year'} to confirm`
      : `Type ${deleteTarget?.name || 'section name'} to confirm`;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Vault" title="Archive" icon="archive">
        <p>Parked school years, sections, and ended duties. Restore returns them to live use. Delete removes unused archive entries; grades stay protected unless you hard delete.</p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        {TABS.map((item) => (
          <button key={item.id} type="button" className={`studio-filter${tab === item.id ? ' is-active' : ''}`} onClick={() => switchTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? <p className="card studio-panel studio-empty">Nothing archived in this list.</p> : null}

      <div className="studio-archive-list">
        {rows.map((row) => (
          <article className="card studio-panel studio-archive-card" key={row.id}>
            <p className="studio-kicker">
              {tab === 'years' ? 'School year' : tab === 'sections' ? row.school_year_label : row.school_year}
            </p>
            <h2>
              <DeskMark name={tab === 'years' ? 'year' : tab === 'sections' ? 'sections' : 'assign'} size={16} />
              {tab === 'years' ? row.label : tab === 'sections' ? sectionLabel(row) : `${row.teacher} · ${row.type === 'adviser' ? 'Adviser' : row.subject}`}
            </h2>
            <p className="studio-empty">
              {tab === 'duties'
                ? `${row.section} · ended ${when(row.ended_at)}`
                : tab === 'sections'
                  ? `${row.delete_summary?.students || row.student_count || 0} enrollments · ${row.delete_summary?.grades || 0} grades`
                  : `${row.delete_summary?.sections || 0} sections · ${row.delete_summary?.grades || 0} grades · archived ${when(row.archived_at)}`}
            </p>
            <div className="studio-actions">
              <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => restore(row)}>
                {busy === String(row.id) ? 'Restoring…' : 'Restore'}
              </button>
              {tab === 'duties' ? (
                <button className="btn btn-danger" type="button" disabled={Boolean(busy)} onClick={() => setDutyDeleteTarget(row)}>
                  Delete permanently
                </button>
              ) : (
                <button className="btn btn-danger" type="button" disabled={Boolean(busy)} onClick={() => openDelete(row)}>
                  Delete permanently
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      {dutyDeleteTarget ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Delete duty permanently?</h2>
            <p>
              Remove <strong>{dutyDeleteTarget.teacher}</strong> ·{' '}
              {dutyDeleteTarget.type === 'adviser' ? 'Adviser' : dutyDeleteTarget.subject} · {dutyDeleteTarget.section}?
              Grade records stay; this only removes the archived duty row.
            </p>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setDutyDeleteTarget(null)}>
                Cancel
              </button>
              <button className="btn btn-danger" type="button" disabled={busy === 'duty-delete'} onClick={submitDutyDelete}>
                {busy === 'duty-delete' ? 'Deleting…' : 'Delete permanently'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteTarget ? (
        <ConfirmDeleteModal
          title={`Delete ${deleteLabel}?`}
          summary={deleteTarget.delete_summary}
          gradesProtected={deleteTarget.grades_protected}
          confirmHint={hardMode || deleteTarget.grades_protected ? confirmHint : 'Optional confirmation label'}
          confirmValue={confirmValue}
          onConfirmValue={setConfirmValue}
          reason={reason}
          onReason={setReason}
          hardMode={hardMode}
          onHardMode={() => setHardMode(true)}
          onCancel={() => setDeleteTarget(null)}
          onSubmit={submitDelete}
          busy={busy === 'delete'}
        />
      ) : null}
    </div>
  );
}
