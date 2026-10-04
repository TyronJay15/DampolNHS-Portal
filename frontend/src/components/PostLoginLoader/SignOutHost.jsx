import { useSyncExternalStore } from 'react';
import SignOutLoader from './SignOutLoader';
import { endSignOut, getSignOut, subscribeSignOut } from './signOutStore';

// Mounted once beside PostLoginHost. Signing out (and the move to /login) is done by the caller;
// this only shows the overlay until it is finished.
export default function SignOutHost() {
  const active = useSyncExternalStore(subscribeSignOut, getSignOut);
  if (!active) return null;
  return <SignOutLoader done={active.done} offline={active.offline} onDone={endSignOut} />;
}
