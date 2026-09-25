import { useEffect, useState } from 'react';
import { fetchCms } from '../services/publicService';

let cached = null;

export function useCms() {
  const [cms, setCms] = useState(null);

  useEffect(() => {
    if (!cached) cached = fetchCms();
    cached.then(setCms).catch(() => setCms(null));
  }, []);

  return cms;
}
