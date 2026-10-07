import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchAuditLogs } from '../../services/adminService';
import {
  AUDIT_FILTERS,
  actionFamily,
  actionLabel,
  chipKind,
  detailLines,
  familyIcon,
  groupAuditRows,
  roleLabel,
  timeLabel,
} from '../../utils/auditTrail';
import './AdminAccountsPage.css';
import './AdminAuditPage.css';

// A link may open the log on one family, for example ?family=guidance from the recommender settings.
function initialFamily(params) {
  const wanted = params.get('family');
  return AUDIT_FILTERS.some((tab) => tab.value === wanted) ? wanted : 'all';
}

export default function AdminAuditPage() {
  const [params] = useSearchParams();
  const [rows, setRows] = useState([]);
  const [family, setFamily] = useState(() => initialFamily(params));
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditLogs()
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const groups = useMemo(() => groupAuditRows(rows, family, query), [family, query, rows]);

  if (loading) return <Loading label="Loading audit log…" />;

  return (
    <div className="desk audit-page">
      <PageHead kicker="Records" title="Audit log" icon="audit">
        <p>School, assignment, placement, grade, account, and announcement actions. These records cannot be edited or deleted.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="audit-filters">
        {AUDIT_FILTERS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            className={family === tab.value ? 'acct-tab is-active' : 'acct-tab'}
            onClick={() => setFamily(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <label className="acct-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search the trail
        </span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Actor, action, or summary"
        />
      </label>

      {groups.length === 0 ? (
        <p className="card acct-empty">{rows.length === 0 ? 'No audit records yet.' : 'No records match that filter.'}</p>
      ) : (
        groups.map((group) => (
          <section className="audit-day" key={group.day}>
            <h2>{group.day}</h2>
            <div className="audit-list">
              {group.rows.map((row) => {
                const family = actionFamily(row);
                const facts = detailLines(row.details);
                return (
                  <article className="card audit-card" key={row.id}>
                    <header className="audit-card-head">
                      <em className={`acct-chip desk-line ${chipKind(family)}`}>
                        <LineMark name={familyIcon(family)} size={14} />
                        {actionLabel(row.action)}
                      </em>
                      <span>{timeLabel(row.created_at)}</span>
                    </header>
                    <dl className="acct-facts">
                      <div>
                        <dt>Who</dt>
                        <dd>{row.actor || '—'}</dd>
                      </div>
                      <div>
                        <dt>Role</dt>
                        <dd>{roleLabel(row.role)}</dd>
                      </div>
                    </dl>
                    <p>{row.summary}</p>
                    {facts.length ? (
                      <dl className="acct-facts audit-detail-facts">
                        {facts.map((fact) => (
                          <div key={`${row.id}-${fact.label}`}>
                            <dt>{fact.label}</dt>
                            <dd>{fact.value}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
