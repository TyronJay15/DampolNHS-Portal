export function shareOf(count, total) {
  if (!total) return 0;
  return Math.round((Number(count) / total) * 100);
}

export function forecastStats(data) {
  const clusters = data?.clusters || [];
  const strands = data?.strands || [];
  const total = Number(data?.grade11_total) || 0;
  const largest = clusters.reduce((best, row) => {
    const score = Number(row.applied ?? row.count) || 0;
    const bestScore = Number(best?.applied ?? best?.count) || 0;
    return !best || score > bestScore ? row : best;
  }, null);
  const smallest = strands.reduce((best, row) => (!best || row.count < best.count ? row : best), null);
  return {
    clusters,
    strands,
    total,
    largest,
    smallest,
    year: data?.school_year || '',
    nextYear: data?.projected_year || '',
    method: data?.method || 'counts',
    ready: Boolean(data?.ready),
    readyReason: data?.ready_reason || '',
    mostApplied: data?.most_applied || null,
  };
}
