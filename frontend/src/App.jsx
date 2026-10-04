import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ConfirmProvider } from './components/ConfirmDialog/ConfirmProvider';
import PostLoginHost from './components/PostLoginLoader/PostLoginHost';
import SignOutHost from './components/PostLoginLoader/SignOutHost';
import ProtectedRoute from './components/ProtectedRoute/ProtectedRoute';
import LandingPage from './pages/public/LandingPage';
import ProgramsPage from './pages/public/ProgramsPage';
import AnnouncementsPage from './pages/public/AnnouncementsPage';
import AboutPage from './pages/public/AboutPage';
import ContactPage from './pages/public/ContactPage';
import LoginPage from './pages/public/LoginPage';
import RegisterPage from './pages/public/RegisterPage';
import ActivatePage from './pages/public/ActivatePage';
import ForgotPasswordPage from './pages/public/ForgotPasswordPage';
import RegistrationWaitingPage from './pages/public/RegistrationWaitingPage';
import HeadLayout from './pages/head/HeadLayout';
import HeadOverview from './pages/head/HeadOverview';
import HeadYearPage from './pages/head/HeadYearPage';
import HeadTermPlanPage from './pages/head/HeadTermPlanPage';
import AccessPage from './pages/access/AccessPage';
import DelegatedWork from './pages/access/DelegatedWork';
import MyAccessPage from './pages/access/MyAccessPage';
import HeadSectionManagePage from './pages/head/HeadSectionManagePage';
import HeadSectionWorkspacePage from './pages/head/HeadSectionWorkspacePage';
import HeadPlacePage from './pages/head/HeadPlacePage';
import HeadAssignPage from './pages/head/HeadAssignPage';
import HeadApprovePage from './pages/head/HeadApprovePage';
import HeadCorrectionsPage from './pages/head/HeadCorrectionsPage';
import HeadArchivePage from './pages/head/HeadArchivePage';
import StudentLayout from './pages/student/StudentLayout';
import StudentOverview from './pages/student/StudentOverview';
import StudentProfilePage from './pages/student/StudentProfilePage';
import StudentGradesPage from './pages/student/StudentGradesPage';
import NotificationsPage from './pages/account/NotificationsPage';
import EventsPage from './pages/events/EventsPage';
import TeacherLayout from './pages/teacher/TeacherLayout';
import TeacherOverview from './pages/teacher/TeacherOverview';
import TeacherClassesPage from './pages/teacher/TeacherClassesPage';
import TeacherClassPage from './pages/teacher/TeacherClassPage';
import TeacherClassRecordsPage from './pages/teacher/TeacherClassRecordsPage';
import TeacherAdvisoryListPage from './pages/teacher/TeacherAdvisoryListPage';
import TeacherAdvisoryPage from './pages/teacher/TeacherAdvisoryPage';
import TeacherAdvisoryRecordsPage from './pages/teacher/TeacherAdvisoryRecordsPage';
import TeacherRecordsPage from './pages/teacher/TeacherRecordsPage';
import AdminLayout from './pages/admin/AdminLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminAccountsLayout from './pages/admin/AdminAccountsLayout';
import AdminAccountsPage from './pages/admin/AdminAccountsPage';
import AdminStaffPage from './pages/admin/AdminStaffPage';
import AdminForecastPage from './pages/admin/AdminForecastPage';
import GradePrintPage from './pages/print/GradePrintPage';
import RecordsPrintPage from './pages/print/RecordsPrintPage';
import AdminAssistantPage from './pages/admin/AdminAssistantPage';
import AdminAuditPage from './pages/admin/AdminAuditPage';
import AdminGradeHistoryPage from './pages/admin/AdminGradeHistoryPage';
import AdminArchivePage from './pages/admin/AdminArchivePage';
import AdminCmsLayout from './pages/admin/cms/AdminCmsLayout';
import AdminCmsLandingPage from './pages/admin/cms/AdminCmsLandingPage';
import AdminCmsAboutPage from './pages/admin/cms/AdminCmsAboutPage';
import AdminCmsContactPage from './pages/admin/cms/AdminCmsContactPage';
import AdminCmsFooterPage from './pages/admin/cms/AdminCmsFooterPage';
import AdminCmsNewsPage from './pages/admin/cms/AdminCmsNewsPage';
import AdminCmsProgramsPage from './pages/admin/cms/AdminCmsProgramsPage';
import ChangePasswordPage from './pages/account/ChangePasswordPage';

export default function App() {
  return (
    <AuthProvider>
      <ConfirmProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/programs" element={<ProgramsPage />} />
            <Route path="/announcements" element={<AnnouncementsPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/activate" element={<ActivatePage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/change-password" element={<Navigate to="/forgot-password" replace />} />
            <Route path="/registration-waiting" element={<RegistrationWaitingPage />} />
            <Route
              path="/student"
              element={
                <ProtectedRoute roles={['student']}>
                  <StudentLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<StudentOverview />} />
              <Route path="profile" element={<StudentProfilePage />} />
              <Route path="grades" element={<StudentGradesPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="password" element={<ChangePasswordPage />} />
            </Route>
            <Route
              path="/teacher"
              element={
                <ProtectedRoute roles={['teacher']}>
                  <TeacherLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<TeacherOverview />} />
              <Route path="classes" element={<TeacherClassesPage />} />
              <Route path="classes/:assignmentId" element={<TeacherClassPage />} />
              <Route path="classes/:assignmentId/records" element={<TeacherClassRecordsPage />} />
              <Route path="advisory" element={<TeacherAdvisoryListPage />} />
              <Route path="advisory/:assignmentId" element={<TeacherAdvisoryPage />} />
              <Route path="advisory/:assignmentId/records" element={<TeacherAdvisoryRecordsPage />} />
              <Route path="records" element={<TeacherRecordsPage />} />
              <Route path="my-access" element={<MyAccessPage />} />
              <Route path="access/:work" element={<DelegatedWork myAccessPath="/teacher/my-access" />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="password" element={<ChangePasswordPage />} />
            </Route>
            <Route
              path="/head"
              element={
                <ProtectedRoute roles={['head_teacher']}>
                  <HeadLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<HeadOverview />} />
              <Route path="year" element={<HeadYearPage />} />
              <Route path="term-plan" element={<HeadTermPlanPage />} />
              <Route path="sections" element={<HeadSectionManagePage />} />
              <Route path="sections/:sectionId/setup" element={<HeadSectionWorkspacePage />} />
              <Route path="place" element={<HeadPlacePage />} />
              <Route path="assign" element={<HeadAssignPage />} />
              <Route path="approve" element={<HeadApprovePage />} />
              <Route path="corrections" element={<HeadCorrectionsPage />} />
              <Route path="archive" element={<HeadArchivePage />} />
              <Route path="access" element={<AccessPage />} />
              <Route path="my-access" element={<MyAccessPage />} />
              <Route path="access/:work" element={<DelegatedWork myAccessPath="/head/my-access" />} />
              <Route path="school" element={<Navigate to="/head/year" replace />} />
              <Route path="grades" element={<Navigate to="/head/approve" replace />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="password" element={<ChangePasswordPage />} />
            </Route>
            <Route
              path="/admin"
              element={
                <ProtectedRoute roles={['admin']}>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<AdminDashboard />} />
              <Route path="accounts" element={<AdminAccountsLayout />}>
                <Route index element={<AdminAccountsPage />} />
                <Route path="staff" element={<AdminStaffPage />} />
              </Route>
              <Route path="forecast" element={<AdminForecastPage />} />
              <Route path="assistant" element={<AdminAssistantPage />} />
              <Route path="audit" element={<AdminAuditPage />} />
              <Route path="access" element={<AccessPage />} />
              <Route path="history" element={<AdminGradeHistoryPage />} />
              <Route path="archive" element={<AdminArchivePage />} />
              <Route path="cms" element={<AdminCmsLayout />}>
                <Route index element={<AdminCmsLandingPage />} />
                <Route path="about" element={<AdminCmsAboutPage />} />
                <Route path="contact" element={<AdminCmsContactPage />} />
                <Route path="footer" element={<AdminCmsFooterPage />} />
                <Route path="news" element={<AdminCmsNewsPage />} />
                <Route path="programs" element={<AdminCmsProgramsPage />} />
              </Route>
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="password" element={<ChangePasswordPage />} />
            </Route>
            <Route
              path="/print/grades"
              element={
                <ProtectedRoute roles={['student', 'teacher', 'head_teacher', 'admin']}>
                  <GradePrintPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/print/records"
              element={
                <ProtectedRoute roles={['teacher', 'head_teacher']}>
                  <RecordsPrintPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <PostLoginHost />
          <SignOutHost />
        </BrowserRouter>
      </ConfirmProvider>
    </AuthProvider>
  );
}
