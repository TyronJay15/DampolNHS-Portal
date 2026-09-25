export default function AccountResultCard({ title, facts = [], next, onClose }) {
  if (!title) return null;

  return (
    <aside className="card acct-result">
      <header className="acct-result-head">
        <h2>{title}</h2>
        <button className="acct-btn" type="button" onClick={onClose}>
          Dismiss
        </button>
      </header>
      {facts.length ? (
        <dl className="acct-facts">
          {facts.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value || '—'}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {next ? <p className="acct-result-next">{next}</p> : null}
    </aside>
  );
}
