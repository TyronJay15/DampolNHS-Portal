import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { homePathForRole } from '../../services/authService';
import Loading from '../Loading/Loading';

export default function ProtectedRoute({ roles, children }) {
  const { user, loading, notice } = useAuth();

  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={notice ? { notice } : undefined} />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }
  return children;
}
