import { useEffect, useState } from 'react';
import { fetchAccessOverview } from '../../services/accessService';

// For the sidebar: how many requests wait for this person, and whether they hold any tag.
export function useAccessSummary() {
  const [summary, setSummary] = useState({ inbox: 0, holds: 0, owns: false });

  useEffect(() => {
    let live = true;
    fetchAccessOverview()
      .then((data) => {
        if (live) setSummary({ inbox: data.inbox_count, holds: data.holds.length, owns: data.owns.length > 0 });
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  return summary;
}
