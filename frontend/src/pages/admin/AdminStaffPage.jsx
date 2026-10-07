import { useEffect, useMemo, useState } from 'react';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import {
  createStaffAccount,
  deactivateAccount,
  fetchStaffAccounts,
  reactivateAccount,
  removeAccount,
  resendStaffActivation,
  resetAuthenticator,
  signOutEverywhere,
} from '../../services/adminService';
import { firstApiError } from '../../utils/authRules';
import AccountListToolbar from './AccountListToolbar';
import AccountResultCard from './AccountResultCard';
import { ActivationFacts, ActivationStrip } from './StaffActivation';
import './AdminAccountsPage.css';

// What happened to an activation email, for the result card.
function codeNext(emailed, then) {
  return emailed
    ? `The 6-digit activation code was emailed. ${then}`
    : 'The code email did not go out. Use Resend, or check the mail settings. The reason shows on their card.';
}

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
  const confirm = useConfirm();
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
    const answer = await confirm({
      title: `Archive ${row.name}?`,
      body: 'Sign-in turns off and they leave Head Teacher lists. You can restore them later.',
      confirmLabel: 'Archive account',
      tone: 'warning',
    });
    if (!answer) return;
    setError('');
    setResult(null);
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

  async function securityAction(row, { title, body, confirmLabel, action, done, next }) {
    const answer = await confirm({ title, body, confirmLabel, tone: 'warning' });
    if (!answer) return;
    setError('');
    setResult(null);
    setSaving(true);
    try {
      await action(row.id);
      setResult({
        title: done,
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Role', value: ROLE_LABEL[row.role] || row.role },
        ],
        next,
      });
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setSaving(false);
    }
  }

  function handleSignOut(row) {
    return securityAction(row, {
      title: `Sign ${row.name} out everywhere?`,
      body: 'Every browser where they are signed in is signed out now. Use it after a lost phone or a shared password.',
      confirmLabel: 'Sign out everywhere',
      action: signOutEverywhere,
      done: 'Signed out everywhere',
      next: 'They can sign in again with their password.',
    });
  }

  function handleResetMfa(row) {
    return securityAction(row, {
      title: `Reset ${row.name}'s authenticator app?`,
      body: 'Use this only after checking in person that they lost their phone and recovery codes. They are signed out and set up the app again at their next sign-in.',
      confirmLabel: 'Reset authenticator',
      action: resetAuthenticator,
      done: 'Authenticator reset',
      next: 'They set up the app again at their next sign-in.',
    });
  }

  async function handleRemove(row) {
    const answer = await confirm({
      title: `Delete ${row.name}?`,
      body: 'This clears the login name and email. Assignments stay. It cannot be undone.',
      confirmLabel: 'Delete permanently',
      tone: 'danger',
    });
    if (!answer) return;
    setError('');
    setResult(null);
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
    const answer = await confirm({
      title: `Reactivate ${row.name}?`,
      body: 'Their account is restored and they appear in the Head Teacher lists again. They may need to set a new password.',
      confirmLabel: 'Reactivate',
    });
    if (!answer) return;
    setError('');
    setResult(null);
    setSaving(true);
    try {
      const saved = await reactivateAccount(row.id);
      setResult({
        title: saved.activation_sent ? 'Staff must set a password' : 'Staff reactivated',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Email', value: row.email },
        ],
        next: saved.activation_sent
          ? codeNext(saved.activation_emailed, 'They open /activate and set a new password.')
          : 'They can sign in again with their existing password.',
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
      const sent = await resendStaffActivation(row.id);
      setResult({
        title: sent.activation_emailed ? 'Activation email sent again' : 'Activation email did not go out',
        facts: [
          { label: 'Name', value: row.name },
          { label: 'Email', value: row.email },
        ],
        next: codeNext(sent.activation_emailed, 'They open /activate and set a password.'),
      });
      await load();
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
        next: codeNext(saved.activation_emailed, 'They open /activate and set a password.'),
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

      <ActivationStrip rows={rows} />

      <div className="acct-staff">
        <form className="card acct-card acct-create" onSubmit={handleCreate}>
          <h2 className="desk-line">
            <LineMark name="staff" />
            New staff login
          </h2>
          <p className="admin-meta">
            No password here. A 6-digit activation code is emailed to them. In local development it also prints in the
            Django terminal.
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
                  <ActivationFacts activation={row.activation} status={row.account_status} />
                  <div className="acct-actions">
                    {row.account_status === 'pending_activation' ? (
                      <button className="acct-btn" type="button" disabled={saving} onClick={() => handleResend(row)}>
                        Resend
                      </button>
                    ) : null}
                    {row.account_status === 'active' ? (
                      <>
                        <button className="acct-btn" type="button" disabled={saving} onClick={() => handleSignOut(row)}>
                          Sign out everywhere
                        </button>
                        {row.role === 'head_teacher' ? (
                          <button className="acct-btn" type="button" disabled={saving} onClick={() => handleResetMfa(row)}>
                            Reset authenticator
                          </button>
                        ) : null}
                        <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => handleArchive(row)}>
                          Archive
                        </button>
                      </>
                    ) : null}
                    {ARCHIVED.has(row.account_status) ? (
                      <>
                        <button className="acct-btn acct-btn-ok" type="button" disabled={saving} onClick={() => handleReactivate(row)}>
                          Reactivate
                        </button>
                        <button className="acct-btn acct-btn-no" type="button" disabled={saving} onClick={() => handleRemove(row)}>
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
    </div>
  );
}
