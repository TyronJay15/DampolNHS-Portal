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
    approvalRate: data?.approval_rate ?? null,
    favored: clusters.find((row) => row.rank === 1 && row.applied) || null,
    year: data?.school_year || '',
    nextYear: data?.projected_year || '',
    curriculum: data?.curriculum || null,
    ready: Boolean(data?.ready),
    readyReason: data?.ready_reason || '',
    model: data?.model || null,
    trend: data?.trend || { status: 'locked', completed_years: 0, required_years: 3, completed_labels: [] },
    weekly: data?.weekly || [],
    retention: data?.retention_rate ?? '100',
    grade12Expected: Number(data?.grade12_expected_total) || 0,
    grade12Sections: Number(data?.grade12_sections_next_year) || 0,
    grade11Sections: Number(data?.grade11_sections_next_year) || 0,
    selection: data?.selection || {},
    demo: Boolean(data?.demo),
    plan: data?.plan || { grade12_curriculum: null, warnings: [] },
    typicalCapacity: Number(data?.typical_capacity) || 40,
  };
}
