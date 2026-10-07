import { NavLink, Outlet, useLocation } from 'react-router-dom';
import Icon from '../../../components/Icon/Icon';
import PageHead from '../../../components/PageHead/PageHead';
import '../../../components/Guidance/Guidance.css';

const TABS = [
  // A program's own page belongs to the Programs tab.
  { to: '/admin/guidance', label: 'Programs', icon: 'guidance', match: (path) => path === '/admin/guidance' || path.startsWith('/admin/guidance/programs/') },
  { to: '/admin/guidance/families', label: 'Families & interests', icon: 'sections' },
  { to: '/admin/guidance/assessment', label: 'Assessment', icon: 'grades' },
  { to: '/admin/guidance/outcomes', label: 'Outcomes', icon: 'place' },
  { to: '/admin/guidance/recommender', label: 'Recommender', icon: 'forecast' },
  { to: '/admin/guidance/settings', label: 'Settings', icon: 'sliders' },
];

export default function AdminGuidanceLayout() {
  const { pathname } = useLocation();
  return (
    <div className="desk studio gd-page">
      <PageHead kicker="College recommendation" title="College course recommender" icon="guidance">
        <p>
          Maintain the program catalog and its sources, the interest assessment and the recommender. Every change is recorded in
          the audit log.
        </p>
      </PageHead>
      <nav className="gd-tabs" aria-label="College recommendation sections">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={Boolean(tab.match)}
            className={({ isActive }) => ((tab.match ? tab.match(pathname) : isActive) ? 'gd-tab is-active' : 'gd-tab')}
          >
            <Icon name={tab.icon} size={16} />
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
