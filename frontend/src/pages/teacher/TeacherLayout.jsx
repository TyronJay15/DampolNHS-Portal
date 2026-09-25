import { Outlet } from 'react-router-dom';
import DashboardShell from '../../components/Sidebar/DashboardShell';
import '../admin/AdminChrome.css';
import '../../styles/studio.css';

export default function TeacherLayout() {
  return (
    <DashboardShell
      title="Teacher"
      initials="TC"
      accountTo="/teacher/password"
      links={[
        { to: '/teacher', label: 'Overview', icon: 'home', end: true },
        { to: '/teacher/classes', label: 'Classes', icon: 'classes' },
        { to: '/teacher/advisory', label: 'Advisory', icon: 'advisory' },
        { to: '/teacher/records', label: 'Records', icon: 'history' },
        { to: '/teacher/notifications', label: 'Notifications', icon: 'bell' },
        { to: '/teacher/events', label: 'Events', icon: 'year' },
      ]}
    >
      <div className="admin-chrome">
        <Outlet />
      </div>
    </DashboardShell>
  );
}
