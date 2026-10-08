import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { onSessionEnd, restore, signIn, signOut } from '../services/session';

const AuthContext = createContext(null);

// Shown on the sign-in page when the sign-in ended by itself.
const END_NOTICES = {
  idle: 'You were signed out after 30 minutes without activity.',
  ended: 'Your sign-in ended. Please sign in again.',
  elsewhere: 'You signed out in another tab.',
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let cancelled = false;
    onSessionEnd((reason) => {
      setUser(null);
      setNotice(END_NOTICES[reason] || '');
    });
    // After a page load the sign-in is restored from the HttpOnly cookie, if there is one.
    restore()
      .then((restored) => {
        if (!cancelled) setUser(restored);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      notice,
      async login(credentials) {
        const result = await signIn(credentials);
        setNotice('');
        setUser(result.user);
        return result;
      },
      async logout() {
        const confirmed = await signOut();
        setUser(null);
        return confirmed;
      },
    }),
    [user, loading, notice]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
