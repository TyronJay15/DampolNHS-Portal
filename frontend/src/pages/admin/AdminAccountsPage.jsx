import { useEffect, useMemo, useState } from 'react';
import { useProposal } from '../../components/Access/proposalContext';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import {
  approveRegistration,
  approveRegistrationsBulk,
  deactivateAccount,
  fetchRegistrationEmails,
  fetchRegistrations,
  reactivateAccount,
  rejectRegistration,
  removeAccount,
  resendRegistrationEmails,
  restoreRejectedToPending,
  setStudentGender,
} from '../../services/adminService';
import { GENDER_OPTIONS, genderLabel } from '../../utils/gender';
import AccountListToolbar from './AccountListToolbar';
import AccountResultCard from './AccountResultCard';
import EmailDelivery, { EmailChip } from './EmailDelivery';
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
    genderLabel(row.gender),
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

function fullName(row) {
  return `${row.first_name} ${row.last_name}`;
}

// While emails are queued, the strip and the chips refresh this often.
const POLL_MS = 8000;

const ONE_EMAIL = {
  sent: 'The email was sent.',
  queued: 'The email is queued and goes out in the background.',
  waiting: "The email waits for tomorrow's allowance.",
  failed: 'The email could not be sent. Use Resend failed in Email delivery.',
};

// One sentence about a batch's emails, from the bulk response's {state: count}.
function batchEmailNote(states) {
  const parts = [
    states.sent ? `${states.sent} sent` : '',
    states.queued ? `${states.queued} queued` : '',
    states.waiting ? `${states.waiting} waiting for tomorrow's allowance` : '',
    states.failed ? `${states.failed} failed` : '',
  ].filter(Boolean);
  if (!parts.length) return '';
  const follow = states.queued || states.waiting ? ' Follow them in Email delivery above.' : '';
  const fix = states.failed ? ' Check the reason on each student, then use Resend failed.' : '';
  return `Emails: ${parts.join(', ')}.${follow}${fix}`;
}

// Background sending only: warn when new emails will not all fit in what is left of today's allowance.
function allowanceWarning(summary, count) {
  if (!summary || summary.delivery !== 'background' || !count) return [];
  const room = Math.max(0, summary.notice_left - summary.queued);
  if (count <= room) return [];
  const effect = 'Approval and rejection still take effect at once.';
  if (!room) {
    return [`Today's email allowance is used up, so ${count === 1 ? 'this email waits' : 'these emails wait'} until tomorrow. ${effect}`];
  }
  return [`${room} of these emails can go out today and ${count - room} will wait until tomorrow. ${effect}`];
}

export default function AdminAccountsPage() {
  const confirm = useConfirm();
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
  // Email delivery summary, Admin only: stays null in proposal mode.
  const [emails, setEmails] = useState(null);
  // Set when a Head Teacher tagged to review registrations opens this page: actions become requests.
  const proposal = useProposal();
  const isProposal = Boolean(proposal);

  async function load(nextStatus = status) {
    setLoading(true);
    setError('');
    try {
      const [data, summary] = await Promise.all([
        fetchRegistrations(nextStatus),
        isProposal ? null : fetchRegistrationEmails(),
      ]);
      setCounts(data.counts || { pending: 0, approved: 0, archived: 0, rejected: 0 });
      setRows(data.results || []);
      setEmails(summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // The latest numbers right before a confirmation, so its allowance warning is current.
  async function freshEmails() {
    if (isProposal) return null;
    try {
      const summary = await fetchRegistrationEmails();
      setEmails(summary);
      return summary;
    } catch {
      return emails;
    }
  }

  useEffect(() => {
    load(status);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  // While emails are queued, refresh the strip and the chips quietly until they are out.
  const queuedEmails = emails?.queued || 0;
  useEffect(() => {
    if (isProposal || !queuedEmails) return undefined;
    const timer = setInterval(async () => {
      try {
        const [summary, data] = await Promise.all([fetchRegistrationEmails(), fetchRegistrations(status)]);
        setEmails(summary);
        setCounts(data.counts || { pending: 0, approved: 0, archived: 0, rejected: 0 });
        setRows(data.results || []);
      } catch {
        // The next tick tries again.
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [isProposal, queuedEmails, status]);

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

  // Proposal mode: the decision is sent to the Admin for approval instead of being applied.
  async function proposeReview(rows, decision) {
    const approving = decision === 'approve';
    const sent = await proposal.propose(
      (note) => ({ decision, registrations: rows.map((row) => row.id), reason: approving ? '' : note }),
      {
        title: approving
          ? `Propose approving ${rows.length === 1 ? fullName(rows[0]) : `${rows.length} students`}?`
          : `Propose rejecting ${fullName(rows[0])}?`,
        facts: [
          { label: 'Students', value: rows.length },
          { label: 'Decision', value: approving ? 'Approve' : 'Reject' },
        ],
        noteLabel: approving ? undefined : 'Reason for rejecting (seen by the Admin and the student)',
      },
    );
    if (!sent) return;
    setResult({
      title: 'Sent for approval',
      facts: [{ label: 'Request', value: sent.summary }],
      next: 'The Admin decides. Follow it under My access.',
    });
  }

  async function handleApprove(row) {
    if (proposal) return proposeReview([row], 'approve');
    const mailbox = await freshEmails();
    const answer = await confirm({
      title: `Approve ${fullName(row)}?`,
      body: `${row.grade_level_enrollment} · ${row.program_code || '—'}. They can sign in right away and receive an approval email and a notification. The Head Teacher then places them in a section.`,
      confirmLabel: 'Approve student',
      warning: allowanceWarning(mailbox, 1),
    });
    if (!answer) return;
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
        next: `They can sign in now with that LRN and the password they registered. ${ONE_EMAIL[saved.email_status] || ''}`,
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleApproveAll() {
    if (proposal) return proposeReview(visible, 'approve');
    // Exactly the students listed on screen are sent, so nobody who registers meanwhile is approved unseen.
    const batch = visible;
    const byGrade = batch.reduce(
      (tally, row) => ({ ...tally, [row.grade_level_enrollment]: (tally[row.grade_level_enrollment] || 0) + 1 }),
      {},
    );
    const left = counts.pending - batch.length;
    const mailbox = await freshEmails();
    const facts = Object.entries(byGrade).map(([label, value]) => ({ label, value }));
    if (mailbox?.delivery === 'background') {
      facts.push({ label: 'Emails used today', value: `${mailbox.used_today} of ${mailbox.notice_limit}` });
    }
    const answer = await confirm({
      title: `Approve ${batch.length} student${batch.length === 1 ? '' : 's'}?`,
      body: 'They can sign in right away, and each student receives an approval email and a notification. The Head Teacher then places them in sections.',
      confirmLabel: `Approve ${batch.length}`,
      facts,
      warning: [
        ...(left > 0
          ? [`Only the ${batch.length} listed students are approved. ${left} other pending registration${left === 1 ? ' is' : 's are'} not included.`]
          : []),
        ...allowanceWarning(mailbox, batch.length),
      ],
    });
    if (!answer) return;
    setBusyId('all');
    setResult(null);
    setError('');
    try {
      const done = await approveRegistrationsBulk(batch.map((row) => row.id));
      const outcome = [{ label: 'Approved', value: done.approved.length }];
      if (done.skipped.length) outcome.push({ label: 'Already reviewed', value: done.skipped.length });
      if (done.failed.length) outcome.push({ label: 'Could not approve', value: done.failed.length });
      const stillPending = Math.max(0, counts.pending - done.approved.length - done.skipped.length);
      if (stillPending) outcome.push({ label: 'Still pending', value: stillPending });
      setResult({
        title: 'Students approved',
        facts: outcome,
        next: `They can sign in now with the password they registered. ${batchEmailNote(done.emails || {})}`,
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleArchive(row) {
    const answer = await confirm({
      title: `Archive ${fullName(row)}?`,
      body: 'Sign-in turns off and they leave Head Teacher and Teacher lists. You can restore them later. Grades stay.',
      confirmLabel: 'Archive account',
      tone: 'warning',
    });
    if (!answer) return;
    setBusyId(row.id);
    setResult(null);
    setError('');
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
    const answer = await confirm({
      title: `Delete ${fullName(row)}?`,
      body: 'This clears the login name and email. Grades stay in the system. It cannot be undone.',
      confirmLabel: 'Delete permanently',
      tone: 'danger',
    });
    if (!answer) return;
    setBusyId(row.id);
    setResult(null);
    setError('');
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
    // Resending a password email to someone who was never activated is routine and needs no question.
    if (row.account_status !== 'pending_activation') {
      const answer = await confirm({
        title: `Reactivate ${fullName(row)}?`,
        body: 'Their account is restored. They may be asked to set a new password, and they appear in the Head Teacher and Teacher lists again.',
        confirmLabel: 'Reactivate',
      });
      if (!answer) return;
    }
    setBusyId(row.id);
    setResult(null);
    setError('');
    try {
      const saved = await reactivateAccount(row.user_id);
      setResult({
        title: saved.activation_sent ? 'Student must set a password' : 'Student reactivated',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'Email', value: row.email },
        ],
        next: saved.activation_sent
          ? 'They must open /activate and set a new password before signing in.'
          : 'They can sign in again with their existing password.',
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  // The admin's correction of a student's gender, e.g. before a DepEd report. Logged in the audit trail.
  async function handleGender(row, gender) {
    const answer = await confirm({
      title: `Set ${fullName(row)}'s gender to ${genderLabel(gender)}?`,
      body: 'This updates the school record used for reports. The student can still change it from My Profile, and every change is logged.',
      confirmLabel: 'Update gender',
      facts: [
        { label: 'Current', value: genderLabel(row.gender) },
        { label: 'New', value: genderLabel(gender) },
      ],
    });
    if (!answer) return;
    setBusyId(row.id);
    setError('');
    try {
      const saved = await setStudentGender(row.user_id, gender);
      setRows((items) => items.map((item) => (item.id === row.id ? { ...item, gender: saved.gender } : item)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleRestorePending(row) {
    const answer = await confirm({
      title: `Restore ${fullName(row)} to pending?`,
      body: 'The registration returns to Pending so you can approve or reject it again. They still cannot sign in until it is approved.',
      confirmLabel: 'Restore to pending',
    });
    if (!answer) return;
    setBusyId(row.id);
    setResult(null);
    setError('');
    try {
      await restoreRejectedToPending(row.user_id);
      setResult({
        title: 'Restored to pending',
        facts: [
          { label: 'Name', value: `${row.first_name} ${row.last_name}` },
          { label: 'LRN', value: row.lrn },
        ],
        next: 'The registration is back in Pending. You can approve or reject again.',
      });
      await load('pending');
      setStatus('pending');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(row) {
    if (proposal) return proposeReview([row], 'reject');
    const mailbox = await freshEmails();
    const answer = await confirm({
      title: `Reject ${fullName(row)}?`,
      body: 'The student will not be able to sign in. Give a reason the school can keep on record.',
      confirmLabel: 'Reject registration',
      tone: 'danger',
      note: { label: 'Reason', required: true, placeholder: 'Why is this registration rejected?' },
      warning: allowanceWarning(mailbox, 1),
    });
    if (!answer) return;
    setBusyId(row.id);
    setResult(null);
    setError('');
    try {
      const saved = await rejectRegistration(row.id, answer.note);
      setResult({
        title: 'Registration rejected',
        facts: [
          { label: 'Name', value: fullName(row) },
          { label: 'LRN', value: row.lrn },
          { label: 'Reason', value: answer.note },
        ],
        next: `They cannot sign in. ${ONE_EMAIL[saved.email_status] || ''}`,
      });
      await load(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleResend() {
    const failed = emails?.failed || 0;
    const answer = await confirm({
      title: `Resend ${failed} failed email${failed === 1 ? '' : 's'}?`,
      body: 'They are queued again with fresh attempts. An address the mail server refused will fail again, so check the reason on each student first.',
      confirmLabel: 'Resend',
      warning: allowanceWarning(emails, failed),
    });
    if (!answer) return;
    setBusyId('resend');
    setResult(null);
    setError('');
    try {
      const done = await resendRegistrationEmails();
      setResult({
        title: 'Emails queued again',
        facts: [{ label: 'Resent', value: done.resent }],
        next:
          done.delivery === 'inline'
            ? 'They were sent again. The chip on each student shows the result.'
            : 'They go out in the background. Email delivery updates by itself.',
      });
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

      <div className="acct-stats" hidden={Boolean(proposal)}>
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

      {isProposal ? null : <EmailDelivery summary={emails} busy={busyId === 'resend'} onResend={handleResend} />}

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
        <label className="acct-search" hidden={Boolean(proposal)}>
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

      {status === 'pending' && visible.length > 0 ? (
        <div className="acct-bulk">
          <p>
            <strong>{visible.length}</strong> pending student{visible.length === 1 ? '' : 's'} listed
          </p>
          <button className="acct-btn acct-btn-ok" type="button" disabled={busyId !== null} onClick={handleApproveAll}>
            {busyId === 'all'
              ? 'Approving…'
              : `${proposal ? 'Propose approving all' : 'Approve all'} (${visible.length})`}
          </button>
        </div>
      ) : null}

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
              <em
                className={`acct-chip${row.account_status === 'suspended' || row.account_status === 'archived' ? ' is-off' : row.account_status === 'pending_activation' ? ' is-wait' : ' is-on'}`}
              >
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
                  <LineMark name="user" size={14} />
                  Gender
                </dt>
                <dd>
                  {proposal ? (
                    genderLabel(row.gender)
                  ) : (
                    <select
                      className="acct-inline-select"
                      aria-label={`Gender of ${fullName(row)}`}
                      value={row.gender || ''}
                      disabled={busyId !== null}
                      onChange={(event) => handleGender(row, event.target.value)}
                    >
                      {row.gender ? null : <option value="">Not set</option>}
                      {GENDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  )}
                </dd>
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
              <div className="acct-review-line">
                <p className="acct-reviewed">Reviewed {formatWhen(row.reviewed_at)}</p>
                <EmailChip delivery={row.email_delivery} />
              </div>
            ) : null}
            {row.email_delivery?.state === 'failed' && row.email_delivery.error ? (
              <p className="acct-reason">Email failed: {row.email_delivery.error}</p>
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
                    {busyId === row.id ? 'Working…' : proposal ? 'Propose approve' : 'Approve'}
                  </button>
                  <button
                    className="acct-btn acct-btn-no"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => handleReject(row)}
                  >
                    {proposal ? 'Propose reject' : 'Reject'}
                  </button>
                </>
              ) : null}
              {row.account_status === 'active' ? (
                <button
                  className="acct-btn acct-btn-no"
                  type="button"
                  disabled={busyId === row.id}
                  onClick={() => handleArchive(row)}
                >
                  Archive
                </button>
              ) : null}
              {row.status === 'rejected' ? (
                <button
                  className="acct-btn"
                  type="button"
                  disabled={busyId === row.id}
                  onClick={() => handleRestorePending(row)}
                >
                  Restore to pending
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
                    Reactivate
                  </button>
                  <button
                    className="acct-btn acct-btn-no"
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => handleRemove(row)}
                  >
                    Delete
                  </button>
                </>
              ) : null}
              {row.account_status === 'pending_activation' && row.status !== 'rejected' ? (
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
    </div>
  );
}
