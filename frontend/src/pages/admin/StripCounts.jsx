/** The small counts in a status strip. A count above zero takes its tone: is-sent, is-queued, is-waiting or is-failed. */
export default function StripCounts({ items }) {
  return (
    <dl className="acct-mail-counts">
      {items.map((item) => (
        <div key={item.key} className={item.value && item.tone ? item.tone : undefined}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
