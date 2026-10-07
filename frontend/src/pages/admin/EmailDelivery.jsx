import LineMark from '../../components/LineMark/LineMark';
import MetricStrip from '../../components/MetricStrip/MetricStrip';

// The oldest queued email waiting this long means the background sender is probably stopped.
const STUCK_MINUTES = 15;

const CHIPS = {
  sent: { tone: 'is-on', label: 'Email sent' },
  queued: { tone: 'is-idle', label: 'Email queued' },
  waiting: { tone: 'is-wait', label: 'Email waits for tomorrow' },
  failed: { tone: 'is-off', label: 'Email failed' },
};

function headline(summary) {
  if (summary.waiting) return "Today's email allowance is used up. The rest go out after midnight.";
  if (summary.queued) return 'Sending in the background. This updates by itself.';
  if (summary.failed) return 'Some emails could not be sent. The reason is shown on each student.';
  return 'Every registration email is out.';
}

/** One registration's result email: a chip, plus the reason when it failed. */
export function EmailChip({ delivery }) {
  if (!delivery) return null;
  const chip = CHIPS[delivery.state] || CHIPS.queued;
  return <em className={`acct-chip ${chip.tone}`}>{chip.label}</em>;
}

/** Admin only: what happened to the approval and rejection emails, today's allowance and Resend. */
export default function EmailDelivery({ summary, busy, onResend }) {
  if (!summary) return null;
  const background = summary.delivery === 'background';
  const counts = [
    { key: 'sent', label: 'Sent today', value: summary.sent_today, icon: 'mail', tone: 'blue' },
    { key: 'queued', label: 'Queued', value: summary.queued, icon: 'history', tone: 'green' },
    { key: 'waiting', label: 'Waiting', value: summary.waiting, icon: 'history', tone: 'gold' },
    { key: 'failed', label: 'Failed', value: summary.failed, icon: 'close', tone: 'red' },
  ];
  const used = Math.min(100, Math.round((summary.used_today / Math.max(1, summary.notice_limit)) * 100));
  const stuck = summary.queued > 0 && summary.oldest_queued_minutes >= STUCK_MINUTES;

  return (
    <section className="acct-mail" aria-label="Registration email delivery">
      <div className="acct-mail-head">
        <span className="desk-line">
          <LineMark name="mail" size={14} />
          Email delivery
        </span>
        <p aria-live="polite">{headline(summary)}</p>
      </div>

      <MetricStrip className="acct-mail-counts" items={counts} />

      {background ? (
        <div className="acct-mail-meter">
          <span>
            Today <strong>{summary.used_today}</strong> of {summary.notice_limit}
          </span>
          <div
            className="acct-mail-track"
            role="meter"
            aria-label="Emails used from today's allowance"
            aria-valuemin={0}
            aria-valuemax={summary.notice_limit}
            aria-valuenow={Math.min(summary.used_today, summary.notice_limit)}
          >
            <i className={used >= 100 ? 'is-full' : undefined} style={{ width: `${used}%` }} />
          </div>
        </div>
      ) : null}

      {summary.failed ? (
        <button className="acct-btn acct-btn-no" type="button" disabled={busy} onClick={onResend}>
          {busy ? 'Resending…' : `Resend failed (${summary.failed})`}
        </button>
      ) : null}

      {stuck ? (
        <p className="acct-mail-warn" role="status">
          The oldest email has waited {summary.oldest_queued_minutes} minutes. The background sender may be stopped.
        </p>
      ) : null}
    </section>
  );
}
