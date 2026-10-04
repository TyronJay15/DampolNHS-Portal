import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Loading from '../../components/Loading/Loading';
import { fetchRecordsPrint } from '../../services/gradeService';
import PrintToolbar from './PrintToolbar';
import { pdfFileName } from './pdfFileName';
import './GradePrintPage.css';

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric' });
}

// A teacher's class grade sheets, or a head teacher's grade decisions, as a printable document.
export default function RecordsPrintPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const sheet = useRef(null);

  useEffect(() => {
    fetchRecordsPrint(Object.fromEntries(params.entries()))
      .then(setReport)
      .catch((err) => setError(err.message));
  }, [params]);

  if (error) {
    return (
      <div className="gp-screen">
        <p className="alert alert-error">{error}</p>
        <button className="btn btn-secondary" type="button" onClick={() => navigate(-1)}>
          Go back
        </button>
      </div>
    );
  }
  if (!report) return <Loading label="Preparing your records…" />;

  return (
    <div className="gp-screen">
      <PrintToolbar
        terms={report.terms}
        fileName={pdfFileName('Grade records', report.person.name, report.school_year, report.term)}
        sheetRef={sheet}
      />

      <article ref={sheet} className="gp-sheet">
        <header className="gp-head">
          <h1>{report.school}</h1>
          <p>Senior High School</p>
          <h2>{report.title}</h2>
        </header>

        <dl className="gp-info">
          <div>
            <dt>Name</dt>
            <dd>{report.person.name}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{report.person.role}</dd>
          </div>
          <div>
            <dt>School year</dt>
            <dd>{report.school_year}</dd>
          </div>
          <div>
            <dt>Term</dt>
            <dd>{report.term}</dd>
          </div>
        </dl>

        {report.groups.length === 0 ? <p className="gp-note">No records for this school year.</p> : null}
        {report.groups.map((group) => (
          <section className="gp-group" key={group.title}>
            <h3>{group.title}</h3>
            <table className="gp-table">
              <thead>
                <tr>
                  {report.columns.map((column) => (
                    <th key={column.key} className={column.num ? 'gp-num' : undefined}>
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {group.rows.length ? (
                  group.rows.map((row, index) => (
                    <tr key={index}>
                      {report.columns.map((column) => (
                        <td key={column.key} className={column.num ? 'gp-num' : undefined}>
                          {row[column.key] || '—'}
                        </td>
                      ))}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={report.columns.length}>No records for this term.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        ))}

        <p className="gp-note">{report.total} record(s). Generated from the school portal; scores are as recorded on the date below.</p>
        <footer className="gp-foot">
          <span>Date generated: {formatDate(report.generated_at)}</span>
        </footer>
      </article>
    </div>
  );
}
