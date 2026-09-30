export function shareOf(count, total) {
  if (!total) return 0;
  return Math.round((Number(count) / total) * 100);
}

export function forecastStats(data) {
  const clusters = data?.clusters || [];
  const strands = data?.strands || [];
  // Charts plot applications (pending + approved) so every screen shows the same numbers.
  const appliedClusters = clusters.map((row) => ({ ...row, count: Number(row.applied ?? row.count) || 0 }));
  const appliedTotal = appliedClusters.reduce((sum, row) => sum + row.count, 0);
  return {
    clusters,
    appliedClusters,
    appliedTotal,
    strands,
    total: Number(data?.grade11_total) || 0,
    favored: clusters.find((row) => row.rank === 1 && row.applied) || null,
    year: data?.school_year || '',
    nextYear: data?.projected_year || '',
    curriculum: data?.curriculum || null,
    ready: Boolean(data?.ready),
    readyReason: data?.ready_reason || '',
    model: data?.model || null,
    plan: data?.plan || { grade12_curriculum: null, warnings: [] },
    typicalCapacity: Number(data?.typical_capacity) || 40,
  };
}
