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
  return (
    <div className="studio-modal-backdrop">
      <div className="card studio-panel studio-modal studio-modal-wide">
        <h2>{title}</h2>
        {summary ? (
          <ul className="studio-summary-list">
            {summary.students != null ? <li>{summary.students} student enrollment record(s)</li> : null}
            {summary.duties != null ? <li>{summary.duties} teacher assignment(s)</li> : null}
            {summary.grades != null ? <li>{summary.grades} grade record(s)</li> : null}
            {summary.sections != null ? <li>{summary.sections} section(s)</li> : null}
          </ul>
        ) : null}
        {gradesProtected && !hardMode ? (
          <>
            <p className="alert alert-error">Grade records are protected on normal delete.</p>
            <button className="btn btn-secondary" type="button" onClick={onHardMode}>
              Hard delete anyway
            </button>
          </>
        ) : null}
        {gradesProtected && hardMode ? (
          <p className="alert alert-error">Hard delete removes grade history permanently for teachers and students.</p>
        ) : null}
        <label className="form-field is-wide">
          <span>{confirmHint}</span>
          <input value={confirmValue} onChange={(event) => onConfirmValue(event.target.value)} />
        </label>
        {(hardMode || gradesProtected) && (
          <label className="form-field is-wide">
            <span>Reason</span>
            <input value={reason} onChange={(event) => onReason(event.target.value)} placeholder="Required for hard delete" />
          </label>
        )}
        <div className="studio-actions">
          <button className="btn btn-secondary" type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-danger" type="button" onClick={onSubmit} disabled={busy}>
            {busy ? 'Deleting…' : hardMode ? 'Hard delete permanently' : 'Delete permanently'}
          </button>
        </div>
      </div>
    </div>
  );
}
