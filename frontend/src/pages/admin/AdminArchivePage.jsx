import { useEffect, useState } from 'react';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import DeskMark from '../../components/DeskMark/DeskMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  fetchAccountArchive,
  reactivateAccount,
  removeAccount,
  restoreRejectedToPending,
} from '../../services/adminService';
import { when } from '../../utils/when';

const TABS = [
  { id: 'students', label: 'Students' },
  { id: 'staff', label: 'Staff' },
];

const ROLE_LABEL = {
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  admin: 'Administrator',
};

export default function AdminArchivePage() {
  const confirm = useConfirm();
  const [tab, setTab] = useState('students');
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load(kind = tab) {
    const data = await fetchAccountArchive(kind);
    setRows(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    load('students')
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function switchTab(next) {
    setTab(next);
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await load(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function nameOf(row) {
    return tab === 'staff' ? row.name : `${row.first_name} ${row.last_name}`;
  }

  async function handleReactivate(row) {
    const answer = await confirm({
      title: `Reactivate ${nameOf(row)}?`,
      body: 'Their account is restored and they appear in the active lists again. They may be asked to set a new password.',
      confirmLabel: 'Reactivate',
    });
    if (!answer) return;
    const userId = row.user_id || row.id;
    setBusy(String(userId));
    setError('');
    setMessage('');
    try {
      const saved = await reactivateAccount(userId);
      setMessage(
        saved.activation_sent
          ? 'Account restored. They must set a password before signing in.'
          : 'Account reactivated. They can sign in with their existing password.',
      );
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function handleRestorePending(row) {
    const answer = await confirm({
      title: `Restore ${nameOf(row)} to pending?`,
      body: 'The registration returns to Pending so you can approve or reject it again. They still cannot sign in until it is approved.',
      confirmLabel: 'Restore to pending',
    });
    if (!answer) return;
    setBusy(String(row.user_id));
    setError('');
    setMessage('');
    try {
      await restoreRejectedToPending(row.user_id);
      setMessage('Student restored to pending. Review them again in Students → Pending.');
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function handleDelete(row) {
    const answer = await confirm({
      title: `Delete ${nameOf(row)} permanently?`,
      body: 'This clears their login details. Grades and school records stay. It cannot be undone.',
      confirmLabel: 'Delete permanently',
      tone: 'danger',
    });
    if (!answer) return;
    const userId = row.user_id || row.id;
    setBusy('delete');
    setError('');
    try {
      await removeAccount(userId);
      setMessage('Account permanently removed.');
      await load(tab);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  if (loading) return <Loading label="Loading account archive…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Vault" title="Account archive" icon="archive">
        <p>
          Archived and rejected student accounts, plus archived staff logins. Restore returns them to active use or
          pending review. Delete clears login details permanently — grades and school records stay.
        </p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`studio-filter${tab === item.id ? ' is-active' : ''}`}
            onClick={() => switchTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? <p className="card studio-panel studio-empty">Nothing in this archive list.</p> : null}

      <div className="studio-archive-list">
        {rows.map((row) => {
          const userId = row.user_id || row.id;
          const isRejected = tab === 'students' && row.archive_kind === 'rejected';
          const title =
            tab === 'staff'
              ? row.name
              : `${row.first_name} ${row.last_name}`;
          return (
            <article className="card studio-panel studio-archive-card" key={`${tab}-${userId}`}>
              <p className="studio-kicker">
                {tab === 'staff'
                  ? ROLE_LABEL[row.role] || row.role
                  : `${row.grade_level_enrollment || '—'} · ${row.program_code || '—'}`}
              </p>
              <h2>
                <DeskMark name={tab === 'staff' ? 'staff' : 'user'} size={16} />
                {title}
              </h2>
              <p className="studio-empty">
                {tab === 'staff'
                  ? `${row.email} · archived ${when(row.archived_at)}`
                  : isRejected
                    ? `Rejected · ${row.rejection_reason || 'No reason recorded'} · ${when(row.archived_at)}`
                    : `${row.lrn || '—'} · archived ${when(row.archived_at)}`}
              </p>
              <div className="studio-actions">
                {isRejected ? (
                  <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => handleRestorePending(row)}>
                    {busy === String(userId) ? 'Restoring…' : 'Restore to pending'}
                  </button>
                ) : (
                  <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => handleReactivate(row)}>
                    {busy === String(userId) ? 'Working…' : 'Reactivate'}
                  </button>
                )}
                <button className="btn btn-danger" type="button" disabled={Boolean(busy)} onClick={() => handleDelete(row)}>
                  Delete permanently
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
