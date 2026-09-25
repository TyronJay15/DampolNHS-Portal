import { NavLink, Outlet } from 'react-router-dom';
import PageHead from '../../components/PageHead/PageHead';
import './AdminAccountsPage.css';

const TABS = [
  { to: '/admin/accounts', label: 'Students', end: true },
  { to: '/admin/accounts/staff', label: 'Teacher Accounts' },
];

export default function AdminAccountsLayout() {
  return (
    <div className="desk admin-accounts">
      <PageHead kicker="Accounts" title="People" icon="user">
        <p>Approve registrations, archive unused logins, then delete only from the archive.</p>
      </PageHead>
      <nav className="acct-tabs">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => (isActive ? 'acct-tab is-active' : 'acct-tab')}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
