import LineMark from '../../components/LineMark/LineMark';

export default function AccountListToolbar({
  query,
  onQuery,
  placeholder,
  sort,
  onSort,
  sorts = [],
  children,
}) {
  return (
    <div className="acct-toolbar">
      {children}
      <label className="acct-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search
        </span>
        <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={placeholder} />
      </label>
      {sorts.length ? (
        <label className="acct-search">
          <span className="desk-line">
            <LineMark name="sections" size={14} />
            Sort
          </span>
          <select value={sort} onChange={(event) => onSort(event.target.value)}>
            {sorts.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </div>
  );
}
