import Icon from '../Icon/Icon';
import './MetricStrip.css';

/** A row of mini-stat cards. Each item: key, label, value, icon (an Icon name) and tone (blue, green, gold, purple or red). */
export default function MetricStrip({ items, className = '' }) {
  return (
    <dl className={`mstat-strip ${className}`.trim()}>
      {items.map((item) => (
        <div key={item.key} className={`mstat is-${item.tone}`}>
          <span className="mstat-icon">
            <Icon name={item.icon} size={15} />
          </span>
          <div>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        </div>
      ))}
    </dl>
  );
}
