import LineMark from '../../components/LineMark/LineMark';
import MetricStrip from '../../components/MetricStrip/MetricStrip';

// Archived and removed accounts are not waiting for anything, so the strip leaves them out.
const COUNTED = new Set(['active', 'pending_activation']);

function shortDay(value) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function shortWhen(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function activationState(activation, status) {
  if (status === 'pending_activation') {
    return `Waiting ${activation.waiting_days} day${activation.waiting_days === 1 ? '' : 's'}`;
  }
  if (activation.activated_times > 1) return `Activated ${activation.activated_times}× · last ${shortDay(activation.activated_at)}`;
  if (activation.activated_at) return `Activated ${shortDay(activation.activated_at)}`;
  return '—';
}

/** Admin only: activation totals for the teachers and the Head Teacher. */
export function ActivationStrip({ rows }) {
  const staff = rows.filter((row) => row.activation && COUNTED.has(row.account_status));
  if (!staff.length) return null;
  const waiting = staff.filter((row) => row.account_status === 'pending_activation').length;
  const failed = staff.filter((row) => row.activation.last_result === 'failed').length;
  const sent = staff.reduce((total, row) => total + row.activation.codes_sent, 0);
  const message = failed
    ? 'Some activation emails failed. The reason is shown on each person.'
    : waiting
      ? 'Waiting staff can be sent a new code with Resend.'
      : 'Every staff account is activated.';

  return (
    <section className="acct-mail" aria-label="Staff activation">
      <div className="acct-mail-head">
        <span className="desk-line">
          <LineMark name="mail" size={14} />
          Staff activation
        </span>
        <p aria-live="polite">{message}</p>
      </div>
      <MetricStrip
        className="acct-mail-counts"
        items={[
          { key: 'staff', label: 'Staff', value: staff.length, icon: 'staff', tone: 'blue' },
          { key: 'activated', label: 'Activated', value: staff.length - waiting, icon: 'check', tone: 'green' },
          { key: 'waiting', label: 'Waiting', value: waiting, icon: 'history', tone: 'gold' },
          { key: 'sent', label: 'Codes sent', value: sent, icon: 'mail', tone: 'purple' },
          { key: 'failed', label: 'Failed', value: failed, icon: 'close', tone: 'red' },
        ]}
      />
    </section>
  );
}

/** One staff member's activation: codes sent, the last attempt, and the activation or the wait. */
export function ActivationFacts({ activation, status }) {
  if (!activation) return null;
  return (
    <>
      <dl className="acct-activation">
        <div>
          <dt>Codes sent</dt>
          <dd>{activation.attempts ? activation.codes_sent : 'No send recorded'}</dd>
        </div>
        <div>
          <dt>Last attempt</dt>
          <dd>{shortWhen(activation.last_attempt_at)}</dd>
        </div>
        <div>
          <dt>Activation</dt>
          <dd>{activationState(activation, status)}</dd>
        </div>
      </dl>
      {activation.last_result === 'failed' ? (
        <p className="acct-reason">Last code email failed: {activation.last_error || 'no reason was given'}</p>
      ) : null}
    </>
  );
}
