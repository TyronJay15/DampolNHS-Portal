import { useEffect, useMemo, useState } from 'react';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import {
  createStaffAccount,
  deactivateAccount,
  fetchStaffAccounts,
  reactivateAccount,
  removeAccount,
  resendStaffActivation,
} from '../../services/adminService';
import { firstApiError } from '../../utils/authRules';
import AccountListToolbar from './AccountListToolbar';
import AccountResultCard from './AccountResultCard';
import './AdminAccountsPage.css';

const EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  role: 'teacher',
};

const ROLE_LABEL = {
  teacher: 'Teacher',
  head_teacher: 'Head teacher',
  admin: 'Administrator',
};

const STATUS_LABEL = {
  pending_activation: 'Needs activation',
  active: 'Active',
  archived: 'Archived',
  suspended: 'Archived',
};

const ARCHIVED = new Set(['archived', 'suspended']);

function initials(row) {
  const parts = String(row.name || '').trim().split(/\s+/);
  return `${parts[0]?.[0] || ''}${parts[1]?.[0] || ''}`.toUpperCase() || 'ST';
}

export default function AdminStaffPage() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState('az');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(null);
  const [removing, setRemoving] = useState(null);
  const hasHeadTeacher = rows.some((row) => row.role === 'head_teacher' && !ARCHIVED.has(row.account_status));

  async function load() {
    setRows(await fetchStaffAccounts());
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      if (needle && !`${row.name} ${row.email} ${row.role}`.toLowerCase().includes(needle)) return false;
      if (role && row.role !== role) return false;
      if (status === 'archived' && !ARCHIVED.has(row.account_status)) return false;
      if (status && status !== 'archived' && row.account_status !== status) return false;
      return true;
    });
    return filtered.slice().sort((a, b) => {
      if (sort === 'az') return (a.name || '').localeCompare(b.name || '');
      return 0;
    });
  }, [query, role, rows, sort, status]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleArchive(row) {
    setError('');
    setResult(null);
    setArchiving(null);
    setSaving(true);
    try {
      await deactivateAccount(row.id);
      setResult({
        title: 'Staff archived',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Email', value: row.email },
          { label: 'Role', value: ROLE_LABEL[row.role] || row.role },
        ],
        next: 'They were emailed and cannot sign in until restored.',
      });
      await load();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(row) {
    setError('');
    setResult(null);
    setRemoving(null);
    setSaving(true);
    try {
      await removeAccount(row.id);
      setResult({
        title: 'Staff removed',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Role', value: ROLE_LABEL[row.role] || row.role },
        ],
        next: 'Login details were cleared. Assignments stay in the archive and this cannot be undone.',
      });
      await load();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleReactivate(row) {
    setError('');
    setResult(null);
    setSaving(true);
    try {
      await reactivateAccount(row.id);
      setResult({
        title: 'Staff must set a password',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Email', value: row.email },
        ],
        next: 'Copy the activation code from the Django terminal, then open /activate and set a new password.',
      });
      await load();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleResend(row) {
    setError('');
    setResult(null);
    setSaving(true);
    try {
      await resendStaffActivation(row.id);
      setResult({
        title: 'Activation email sent again',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Email', value: row.email },
        ],
        next: 'Copy the activation code from the Django terminal, then open /activate.',
      });
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleCreate(event) {
    event.preventDefault();
    setError('');
    setResult(null);
    setSaving(true);
    try {
      const saved = await createStaffAccount(form);
      setForm(EMPTY);
      setResult({
        title: 'Staff account created',
        facts: [
          { label: 'Name', value: saved.name },
          { label: 'Email', value: saved.email },
          { label: 'Role', value: ROLE_LABEL[saved.role] || saved.role },
        ],
        next: 'Copy the 6-digit activation code from the Django terminal, then open /activate and set a password.',
      });
      await load();
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading label="Loading staff…" />;

  return (
    <div>
      {result ? <AccountResultCard {...result} onClose={() => setResult(null)} /> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="acct-staff">
        <form className="card acct-card acct-create" onSubmit={handleCreate}>
          <h2 className="desk-line">
            <LineMark name="staff" />
            New staff login
          </h2>
          <p className="admin-meta">
            No password here. The 6-digit activation code prints in the Django terminal until school DNS is ready.
          </p>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="user" size={14} />
              First name
            </span>
            <input required value={form.first_name} onChange={(event) => update('first_name', event.target.value)} />
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="user" size={14} />
              Last name
            </span>
            <input required value={form.last_name} onChange={(event) => update('last_name', event.target.value)} />
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="mail" size={14} />
              Email
            </span>
            <input type="email" required value={form.email} onChange={(event) => update('email', event.target.value)} />
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="assign" size={14} />
              Role
            </span>
            <select value={form.role} onChange={(event) => update('role', event.target.value)}>
              <option value="teacher">Teacher</option>
              <option value="head_teacher" disabled={hasHeadTeacher}>
                Head teacher{hasHeadTeacher ? ' (already created)' : ''}
              </option>
            </select>
          </label>
          <button className="acct-btn acct-btn-ok" type="submit" disabled={saving}>
            {saving ? 'Sending…' : 'Create and email code'}
          </button>
        </form>

        <div>
          <AccountListToolbar
            query={query}
            onQuery={setQuery}
            placeholder="Name, email, or role"
            sort={sort}
            onSort={setSort}
            sorts={[{ value: 'az', label: 'A–Z' }]}
          >
            <label className="acct-search">
              <span className="desk-line">
                <LineMark name="assign" size={14} />
                Role
              </span>
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="">All roles</option>
                <option value="teacher">Teacher</option>
                <option value="head_teacher">Head teacher</option>
                <option value="admin">Administrator</option>
              </select>
            </label>
            <label className="acct-search">
              <span className="desk-line">
                <LineMark name="account" size={14} />
                Status
              </span>
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="pending_activation">Needs activation</option>
                <option value="archived">Archived</option>
              </select>
            </label>
          </AccountListToolbar>
          {visible.length === 0 ? (
            <p className="card acct-empty">{rows.length === 0 ? 'No staff accounts yet.' : 'No staff matches that search.'}</p>
          ) : (
            <div className="acct-staff-list">
              {visible.map((row) => (
                <article className="card acct-card" key={row.id}>
                  <header className="acct-card-head">
                    <span className="acct-avatar">{initials(row)}</span>
                    <div>
                      <h2 className="desk-line">
                        <LineMark name="staff" />
                        {row.name}
                      </h2>
                      <p>{row.email}</p>
                    </div>
                    <em
                      className={`acct-chip${ARCHIVED.has(row.account_status) ? ' is-off' : row.account_status === 'pending_activation' ? ' is-wait' : ' is-on'}`}
                    >
                      {STATUS_LABEL[row.account_status] || row.account_status}
                    </em>
                  </header>
                  <p className="acct-role">{ROLE_LABEL[row.role] || row.role}</p>
                  <div className="acct-actions">
                    {row.account_status === 'pending_activation' ? (
                      <button className="acct-btn" type="button" disabled={saving} onClick={() => handleResend(row)}>
                        Resend
                      </button>
                    ) : null}
                    {row.account_status === 'active' ? (
                      <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => setArchiving(row)}>
                        Archive
                      </button>
                    ) : null}
                    {ARCHIVED.has(row.account_status) ? (
                      <>
                        <button className="acct-btn acct-btn-ok" type="button" disabled={saving} onClick={() => handleReactivate(row)}>
                          Restore
                        </button>
                        <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => setRemoving(row)}>
                          Delete
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>

      {archiving ? (
        <div className="admin-modal-backdrop">
          <div className="card admin-modal">
            <h2 className="desk-line">
              <LineMark name="staff" />
              Archive {archiving.name}?
            </h2>
            <p>Sign-in turns off and they leave Head Teacher lists. Restore later if needed.</p>
            <div className="acct-actions">
              <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => handleArchive(archiving)}>
                Archive account
              </button>
              <button className="acct-btn" type="button" onClick={() => setArchiving(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {removing ? (
        <div className="admin-modal-backdrop">
          <div className="card admin-modal">
            <h2 className="desk-line">
              <LineMark name="staff" />
              Delete {removing.name}?
            </h2>
            <p>This clears the login name and email. Assignments stay. It cannot be undone.</p>
            <div className="acct-actions">
              <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => handleRemove(removing)}>
                Delete permanently
              </button>
              <button className="acct-btn" type="button" onClick={() => setRemoving(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
