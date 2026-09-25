import { Outlet } from 'react-router-dom';
import DashboardShell from '../../components/Sidebar/DashboardShell';
import '../admin/AdminChrome.css';
import '../../styles/studio.css';

export default function HeadLayout() {
  return (
    <DashboardShell
      title="Head Teacher"
      initials="HT"
      accountTo="/head/password"
      links={[
        { to: '/head', label: 'Overview', icon: 'home', end: true },
        { to: '/head/year', label: 'School year', icon: 'year' },
        { to: '/head/sections', label: 'Sections', icon: 'sections' },
        { to: '/head/place', label: 'Place students', icon: 'place' },
        { to: '/head/assign', label: 'Assign teachers', icon: 'assign' },
        { to: '/head/approve', label: 'Approve grades', icon: 'approve' },
        { to: '/head/corrections', label: 'Corrections', icon: 'corrections' },
        { to: '/head/archive', label: 'Archive', icon: 'archive' },
        { to: '/head/notifications', label: 'Notifications', icon: 'bell' },
        { to: '/head/events', label: 'Events', icon: 'year' },
      ]}
    >
      <div className="admin-chrome">
        <Outlet />
      </div>
    </DashboardShell>
  );
}
