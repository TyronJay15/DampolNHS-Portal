import { Outlet } from 'react-router-dom';
import DashboardShell from '../../components/Sidebar/DashboardShell';
import './AdminChrome.css';
import '../../styles/studio.css';

export default function AdminLayout() {
  return (
    <DashboardShell
      title="Admin Dashboard"
      initials="AD"
      accountTo="/admin/password"
      links={[
        { to: '/admin', label: 'Dashboard', icon: 'home', end: true },
        { to: '/admin/accounts', label: 'Students', icon: 'user', end: true },
        { to: '/admin/accounts/staff', label: 'Teacher Accounts', icon: 'staff' },
        { to: '/admin/archive', label: 'Archive', icon: 'archive' },
        { to: '/admin/forecast', label: 'Grade 11 forecast', icon: 'forecast' },
        { to: '/admin/assistant', label: 'Assistant', icon: 'bell' },
        { to: '/admin/audit', label: 'Audit log', icon: 'audit' },
        { to: '/admin/history', label: 'Grade history', icon: 'history' },
        { to: '/admin/cms', label: 'Website CMS', icon: 'cms' },
        { to: '/admin/notifications', label: 'Notifications', icon: 'bell' },
        { to: '/admin/events', label: 'Events', icon: 'year' },
      ]}
    >
      <div className="admin-chrome">
        <Outlet />
      </div>
    </DashboardShell>
  );
}
