import { useEffect, useMemo, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import {
  approveRegistration,
  deactivateAccount,
  fetchRegistrations,
  reactivateAccount,
  rejectRegistration,
  removeAccount,
} from '../../services/adminService';
import AccountListToolbar from './AccountListToolbar';
import AccountResultCard from './AccountResultCard';
import './AdminAccountsPage.css';

const FILTERS = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Active' },
  { value: 'archived', label: 'Archived' },
  { value: 'rejected', label: 'Rejected' },
];

function formatWhen(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function initials(row) {
  return `${row.first_name?.[0] || ''}${row.last_name?.[0] || ''}`.toUpperCase() || 'ST';
}

function loginLabel(status) {
  if (status === 'suspended' || status === 'archived') return 'Archived';
  if (status === 'pending_activation') return 'Needs password';
  if (status === 'removed') return 'Removed';
  return 'Active';
}

function uniqueValues(rows, key) {
  return [...new Set(rows.map((row) => row[key]).filter(Boolean))].sort();
}

function compareName(a, b) {
  return `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`);
}

function matchesSearch(row, query) {
  if (!query) return true;
  const hay = [
    row.first_name,
    row.last_name,
    row.lrn,
    row.email,
    row.program_code,
    row.contact_number,
    row.address,
    row.guardian_name,
  ]
    .join(' ')
    .toLowerCase();
  return hay.includes(query);
}

export default function AdminAccountsPage() {
  const [status, setStatus] = useState('pending');
  const [counts, setCounts] = useState({ pending: 0, approved: 0, archived: 0, rejected: 0 });
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [grade, setGrade] = useState('');
  const [program, setProgram] = useState('');
  const [login, setLogin] = useState('');
  const [sort, setSort] = useState('az');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [rejecting, setRejecting] = useState(null);
  const [archiving, setArchiving] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [reason, setReason] = useState('');

  async function load(nextStatus = status) {
    setLoading(true);
    setError('');
    try {
      const data = await fetchRegistrations(nextStatus);
      setCounts(data.counts || { pending: 0, approved: 0, archived: 0, rejected: 0 });
      setRows(data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(status);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      if (!matchesSearch(row, needle)) return false;
      if (grade && row.grade_level_enrollment !== grade) return false;
      if (program && row.program_code !== program) return false;
      if (login === 'archived' && !['archived', 'suspended'].includes(row.account_status)) return false;
      if (login && login !== 'archived' && row.account_status !== login) return false;
      return true;
    });
    return filtered.slice().sort((a, b) => {
      if (sort === 'newest') {
        return new Date(b.submitted_at || 0) - new Date(a.submitted_at || 0);
      }
      return compareName(a, b);
    });
  }, [grade, login, program, query, rows, sort]);

  async function handleApprove(row) {
    setBusyId(row.id);
    setResult(null);
    setError('');
    try {
      const saved = await approveRegistration(row.id);
      setResult({
        title: 'Student approved',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'LRN', value: row.lrn },
          { label: 'Program', value: `${row.grade_level_enrollment} · ${row.program_code || '—'}` },
        ],
        next:
          saved.email_sent === false
            ? 'They can sign in now, but the approval email did not send. Check SMTP and ask them to use their registered password.'
            : 'They can sign in now with that LRN and the password they registered. An approval email was sent.',
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleArchive(row) {
    setBusyId(row.id);
    setResult(null);
    setError('');
    setArchiving(null);
    try {
      await deactivateAccount(row.user_id);
      setResult({
        title: row.status === 'pending' ? 'Pending student archived' : 'Student archived',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'LRN', value: row.lrn },
          { label: 'Email', value: row.email },
        ],
        next:
          row.status === 'pending'
            ? 'The registration was also rejected. They cannot sign in.'
            : 'They were emailed and cannot sign in until restored.',
      });
      await load(row.status === 'pending' ? 'rejected' : 'archived');
      setStatus(row.status === 'pending' ? 'rejected' : 'archived');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleRemove(row) {
    setBusyId(row.id);
    setResult(null);
    setError('');
    setRemoving(null);
    try {
      await removeAccount(row.user_id);
      setResult({
        title: 'Student removed',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'LRN', value: row.lrn },
        ],
        next: 'Login details were cleared. Grades stay in the archive and this cannot be undone.',
      });
      await load('archived');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReactivate(row) {
    setBusyId(row.id);
    setResult(null);
    setError('');
    try {
      await reactivateAccount(row.user_id);
      setResult({
        title: 'Student must set a password',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'Email', value: row.email },
        ],
        next: 'They must open /activate and set a new password before signing in.',
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(event) {
    event.preventDefault();
    if (!rejecting) return;
    setBusyId(rejecting.id);
    setResult(null);
    setError('');
    try {
      const saved = await rejectRegistration(rejecting.id, reason);
      setResult({
        title: 'Registration rejected',
        facts: [
          { label: 'Name', value: `${rejecting.first_name} ${rejecting.last_name}` },
          { label: 'LRN', value: rejecting.lrn },
          { label: 'Reason', value: reason },
        ],
        next:
          saved.email_sent === false
            ? 'They cannot sign in. The rejection email did not send — tell them in person as well.'
            : 'They cannot sign in. A rejection email was sent.',
      });
      setRejecting(null);
      setReason('');
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      {result ? <AccountResultCard {...result} onClose={() => setResult(null)} /> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="acct-stats">
        {FILTERS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            className={`acct-stat${status === tab.value ? ' is-active' : ''}${tab.value === 'pending' ? ' is-pending' : ''}${tab.value === 'approved' ? ' is-ok' : ''}`}
            onClick={() => {
              setStatus(tab.value);
              setGrade('');
              setProgram('');
              setLogin('');
              setLoading(true);
            }}
          >
            <span className="desk-stat-top">
              <DeskMark
                name={tab.value === 'pending' ? 'user' : tab.value === 'approved' ? 'check' : 'archive'}
                size={16}
              />
              {tab.label}
            </span>
            <strong>{counts[tab.value] ?? 0}</strong>
          </button>
        ))}
      </div>

      <AccountListToolbar
        query={query}
        onQuery={setQuery}
        placeholder="Name, LRN, email, or program"
        sort={sort}
        onSort={setSort}
        sorts={[
          { value: 'az', label: 'A–Z' },
          { value: 'newest', label: 'Newest' },
        ]}
      >
        <label className="acct-search">
          <span className="desk-line">
            <LineMark name="classes" size={14} />
            Grade
          </span>
          <select value={grade} onChange={(event) => setGrade(event.target.value)}>
            <option value="">All grades</option>
            {uniqueValues(rows, 'grade_level_enrollment').map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="acct-search">
          <span className="desk-line">
            <LineMark name="sections" size={14} />
            Program
          </span>
          <select value={program} onChange={(event) => setProgram(event.target.value)}>
            <option value="">All programs</option>
            {uniqueValues(rows, 'program_code').map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="acct-search">
          <span className="desk-line">
            <LineMark name="account" size={14} />
            Login
          </span>
          <select value={login} onChange={(event) => setLogin(event.target.value)}>
            <option value="">All logins</option>
            <option value="active">Active</option>
            <option value="pending_activation">Needs password</option>
            <option value="archived">Archived</option>
          </select>
        </label>
      </AccountListToolbar>

      {loading ? <p className="admin-empty">Loading accounts…</p> : null}
      {!loading && visible.length === 0 ? (
        <p className="card acct-empty">
          {rows.length === 0 ? `No ${status} students.` : 'No student matches that search.'}
        </p>
      ) : null}

      <div className="acct-grid">
        {visible.map((row) => (
          <article className="card acct-card" key={row.id}>
            <header className="acct-card-head">
              <span className="acct-avatar">{initials(row)}</span>
              <div>
                <h2 className="desk-line">
                  <LineMark name="user" />
                  {row.first_name} {row.last_name}
                </h2>
                <p>
                  {row.grade_level_enrollment} · {row.program_code || '—'}
                </p>
              </div>
              <em className={`acct-chip${row.account_status === 'suspended' || row.account_status === 'archived' ? ' is-off' : row.account_status === 'pending_activation' ? ' is-wait' : ' is-on'}`}>
                {loginLabel(row.account_status)}
              </em>
            </header>

            <dl className="acct-facts">
              <div>
                <dt className="desk-line">
                  <LineMark name="user" size={14} />
                  LRN
                </dt>
                <dd>{row.lrn || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="mail" size={14} />
                  Email
                </dt>
                <dd>{row.email || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="phone" size={14} />
                  Contact
                </dt>
                <dd>{row.contact_number || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="guardian" size={14} />
                  Guardian
                </dt>
                <dd>{row.guardian_name || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="phone" size={14} />
                  Guardian contact
                </dt>
                <dd>{row.guardian_contact || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="home" size={14} />
                  Address
                </dt>
                <dd>{row.address || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="year" size={14} />
                  Submitted
                </dt>
                <dd>{formatWhen(row.submitted_at)}</dd>
              </div>
            </dl>

            {row.status === 'rejected' && row.rejection_reason ? (
              <p className="acct-reason">Reason: {row.rejection_reason}</p>
            ) : null}
            {row.status !== 'pending' ? (
              <p className="acct-reviewed">Reviewed {formatWhen(row.reviewed_at)}</p>
            ) : null}

            <div className="acct-actions">
              {row.status === 'pending' ? (
                <>
                  <button
                    className="acct-btn acct-btn-ok"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => handleApprove(row)}
                  >
                    {busyId === row.id ? 'Working…' : 'Approve'}
                  </button>
                  <button
                    className="acct-btn acct-btn-no"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => {
                      setRejecting(row);
                      setReason('');
                    }}
                  >
                    Reject
                  </button>
                </>
              ) : null}
              {row.account_status === 'active' ? (
                <button
                  className="acct-btn acct-btn-no"
                  type="button"
                  disabled={busyId === row.id}
                  onClick={() => setArchiving(row)}
                >
                  Archive
                </button>
              ) : null}
              {row.account_status === 'archived' || row.account_status === 'suspended' ? (
                <>
                  <button
                    className="acct-btn"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => handleReactivate(row)}
                  >
                    Restore
                  </button>
                  <button
                    className="acct-btn acct-btn-no"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => setRemoving(row)}
                  >
                    Delete
                  </button>
                </>
              ) : null}
              {row.account_status === 'pending_activation' ? (
                <button
                  className="acct-btn"
                  type="button"
                  disabled={busyId === row.id}
                  onClick={() => handleReactivate(row)}
                >
                  Resend password email
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>

      {archiving ? (
        <div className="admin-modal-backdrop">
          <div className="card admin-modal">
            <h2 className="desk-line">
              <LineMark name="user" />
              Archive {archiving.first_name} {archiving.last_name}?
            </h2>
            <p>Sign-in turns off and they leave Head Teacher and Teacher lists. Restore later if needed. Grades stay.</p>
            <div className="acct-actions">
              <button
                className="acct-btn acct-btn-no"
                type="button"
                disabled={busyId === archiving.id}
                onClick={() => handleArchive(archiving)}
              >
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
              <LineMark name="user" />
              Delete {removing.first_name} {removing.last_name}?
            </h2>
            <p>This clears the login name and email. Grades stay in the system. It cannot be undone.</p>
            <div className="acct-actions">
              <button
                className="acct-btn acct-btn-no"
                type="button"
                disabled={busyId === removing.id}
                onClick={() => handleRemove(removing)}
              >
                Delete permanently
              </button>
              <button className="acct-btn" type="button" onClick={() => setRemoving(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {rejecting ? (
        <div className="admin-modal-backdrop">
          <form className="card admin-modal" onSubmit={handleReject}>
            <h2 className="desk-line">
              <LineMark name="user" />
              Reject {rejecting.first_name} {rejecting.last_name}?
            </h2>
            <p>The student will not be able to sign in. Give a reason the school can keep on record.</p>
            <label className="form-field">
              <span className="desk-line">
                <LineMark name="cms" size={14} />
                Reason
              </span>
              <textarea value={reason} onChange={(event) => setReason(event.target.value)} required rows={4} />
            </label>
            <div className="acct-actions">
              <button className="acct-btn acct-btn-no" type="submit" disabled={busyId === rejecting.id}>
                Confirm reject
              </button>
              <button className="acct-btn" type="button" onClick={() => setRejecting(null)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
