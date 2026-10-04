// Term tabs for a teacher duty. With no scheduled term it explains why instead of showing empty tabs.
export default function DutyTermTabs({ terms, termId, onChange, label = (term) => term.label, empty }) {
  if (!terms.length) {
    return (
      <p className="card studio-panel studio-empty">
        {empty || 'No term is scheduled for this yet. The Head Teacher sets it in the term plan.'}
      </p>
    );
  }
  return (
    <div className="studio-tabs">
      {terms.map((term) => (
        <button
          key={term.id}
          type="button"
          className={String(term.id) === termId ? 'is-active' : ''}
          onClick={() => onChange(String(term.id))}
        >
          {label(term)}
        </button>
      ))}
    </div>
  );
}
