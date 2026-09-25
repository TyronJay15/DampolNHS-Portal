import { useEffect, useState } from 'react';

const KEY = 'dampol-theme';

function readTheme() {
  try {
    return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(readTheme);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      // Preference is optional if storage is blocked.
    }
  }, [theme]);

  function toggle() {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }

  return { theme, toggle };
}
