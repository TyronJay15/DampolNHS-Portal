import { NavLink, Outlet } from 'react-router-dom';
import PageHead from '../../../components/PageHead/PageHead';
import './AdminCms.css';

const TABS = [
  { to: '/admin/cms', label: 'Landing', end: true },
  { to: '/admin/cms/about', label: 'About' },
  { to: '/admin/cms/contact', label: 'Contact' },
  { to: '/admin/cms/footer', label: 'Footer' },
  { to: '/admin/cms/news', label: 'News' },
  { to: '/admin/cms/programs', label: 'Programs' },
];

export default function AdminCmsLayout() {
  return (
    <div className="desk admin-cms">
      <PageHead kicker="Website CMS" title="Public pages" icon="cms">
        <p>Edit copy and photos here. Each tab saves only that section.</p>
      </PageHead>
      <nav className="cms-tabs">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => (isActive ? 'cms-tab is-active' : 'cms-tab')}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
