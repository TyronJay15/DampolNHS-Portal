import { useCallback, useSyncExternalStore } from 'react';
import { useNavigate } from 'react-router-dom';
import { homePathForRole } from '../../services/authService';
import PostLoginLoader from './PostLoginLoader';
import { endPostLogin, getPostLogin, subscribePostLogin } from './postLoginStore';

// Mounted once inside the router. It only chooses when to move on; the destination is still the path
// the existing role routing gives, and the dashboard's own ProtectedRoute decides access.
export default function PostLoginHost() {
  const active = useSyncExternalStore(subscribePostLogin, getPostLogin);
  const navigate = useNavigate();
  const role = active?.role;
  const leave = useCallback(() => navigate(homePathForRole(role)), [navigate, role]);

  if (!active) return null;
  return <PostLoginLoader role={role} onLeave={leave} onDone={endPostLogin} />;
}
