export default function YearChip({ user, className = 'studio-chip' }) {
  const label = user?.current_school_year?.label;
  if (!label) return null;
  return <span className={className}>{label}</span>;
}
