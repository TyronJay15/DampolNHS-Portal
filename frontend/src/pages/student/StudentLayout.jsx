import { Outlet } from 'react-router-dom';
import DashboardShell from '../../components/Sidebar/DashboardShell';

export default function StudentLayout() {
  return (
    <DashboardShell
      title="Student Dashboard"
      initials="ST"
      accountTo="/student/password"
      links={[
        { to: '/student', label: 'Overview', icon: 'home', end: true },
        { to: '/student/profile', label: 'My Profile', icon: 'user' },
        { to: '/student/grades', label: 'Grades', icon: 'grades' },
        { to: '/student/guidance', label: 'College recommendation', icon: 'guidance' },
        { to: '/student/notifications', label: 'Notifications', icon: 'bell' },
        { to: '/student/events', label: 'Events', icon: 'year' },
      ]}
    >
      <Outlet />
    </DashboardShell>
  );
}
