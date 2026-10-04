import { Link } from 'react-router-dom';
import './MoreMenu.css';

// A quiet "⋯" menu for occasional actions such as printing, kept out of the main layout.
// items: [{ to, label }]
export default function MoreMenu({ items }) {
  if (!items.length) return null;
  return (
    <details className="more-menu">
      <summary aria-label="More actions">⋯</summary>
      <div className="more-menu-list">
        {items.map((item) => (
          <Link key={item.to} to={item.to}>
            {item.label}
          </Link>
        ))}
      </div>
    </details>
  );
}
