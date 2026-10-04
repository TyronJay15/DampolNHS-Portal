import ConfirmFrame from '../ConfirmDialog/ConfirmFrame';
import Icon from '../Icon/Icon';

const COUNTS = [
  ['students', 'Student records'],
  ['duties', 'Teacher duties'],
  ['grades', 'Grade records'],
  ['sections', 'Sections'],
];

// Permanent delete with a typed confirmation, and a reason when grade history is also removed.
// It is built on the shared ConfirmFrame so it looks and behaves like every other confirmation.
export default function ConfirmDeleteModal({
  title,
  summary,
  gradesProtected,
  confirmHint,
  confirmValue,
  onConfirmValue,
  reason,
  onReason,
  hardMode,
  onHardMode,
  onCancel,
  onSubmit,
  busy,
}) {
  const facts = COUNTS.filter(([key]) => summary?.[key] != null).map(([key, label]) => ({ label, value: summary[key] }));
  return (
    <ConfirmFrame
      title={title}
      tone="danger"
      wide
      onDismiss={busy ? undefined : onCancel}
      actions={
        <>
          <button type="button" className="cfm-btn is-cancel" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          {gradesProtected && !hardMode ? (
            <button type="button" className="cfm-btn is-cancel" onClick={onHardMode} disabled={busy}>
              Hard delete anyway
            </button>
          ) : null}
          <button type="button" className="cfm-btn is-confirm" onClick={onSubmit} disabled={busy}>
            {busy ? 'Deleting…' : hardMode ? 'Hard delete permanently' : 'Delete permanently'}
          </button>
        </>
      }
    >
      {facts.length ? (
        <dl className="cfm-facts">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dd>{fact.value}</dd>
              <dt>{fact.label}</dt>
            </div>
          ))}
        </dl>
      ) : null}

      {gradesProtected ? (
        <div className="cfm-warning is-danger" role="note">
          <Icon name="alert" size={16} />
          <p>
            {hardMode
              ? 'Hard delete removes grade history permanently for teachers and students.'
              : 'Grade records are protected on normal delete.'}
          </p>
        </div>
      ) : null}

      <label className="cfm-field">
        <span>{confirmHint}</span>
        <input data-autofocus value={confirmValue} onChange={(event) => onConfirmValue(event.target.value)} />
      </label>
      {hardMode || gradesProtected ? (
        <label className="cfm-field">
          <span>Reason</span>
          <input value={reason} onChange={(event) => onReason(event.target.value)} placeholder="Required for hard delete" />
        </label>
      ) : null}
    </ConfirmFrame>
  );
}
