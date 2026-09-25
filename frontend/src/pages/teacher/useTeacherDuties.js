import { useEffect, useState } from 'react';
import { fetchTeacherAssignments } from '../../services/teacherService';

export function useTeacherDuties() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeacherAssignments()
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return {
    rows,
    encode: rows.filter((row) => row.can_encode),
    advise: rows.filter((row) => row.can_advise),
    error,
    loading,
  };
}
