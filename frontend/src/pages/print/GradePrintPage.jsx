import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Loading from '../../components/Loading/Loading';
import { fetchGradePrint } from '../../services/gradeService';
import PrintFooter from './PrintFooter';
import PrintToolbar from './PrintToolbar';
import { pdfFileName } from './pdfFileName';
import './GradePrintPage.css';

// A standalone document page: no dashboard shell, so nothing but the report is printed.
export default function GradePrintPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const sheet = useRef(null);

  useEffect(() => {
    const query = Object.fromEntries(params.entries());
    fetchGradePrint(query)
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
  if (!report) return <Loading label="Preparing your grade report…" />;

  const { student } = report;
  return (
    <div className="gp-screen">
      <PrintToolbar
        terms={report.terms}
        fileName={pdfFileName('Grades', student.name, report.school_year, report.term)}
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
            <dt>Learner</dt>
            <dd>{student.name}</dd>
          </div>
          <div>
            <dt>LRN</dt>
            <dd>{student.lrn || '—'}</dd>
          </div>
          <div>
            <dt>Grade level</dt>
            <dd>{student.grade_level || '—'}</dd>
          </div>
          <div>
            <dt>Section</dt>
            <dd>{student.section || '—'}</dd>
          </div>
          <div>
            <dt>Program / Strand</dt>
            <dd>{student.program ? `${student.program} — ${student.program_name}` : '—'}</dd>
          </div>
          <div>
            <dt>School year</dt>
            <dd>{report.school_year || '—'}</dd>
          </div>
          <div>
            <dt>Term</dt>
            <dd>{report.term}</dd>
          </div>
        </dl>

        <table className="gp-table">
          <thead>
            <tr>
              <th>Term</th>
              <th>Subject</th>
              <th>Teacher</th>
              <th className="gp-num">Grade</th>
              <th>Remarks</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.length ? (
              report.rows.map((row) => (
                <tr key={`${row.term}-${row.subject}`}>
                  <td>{row.term}</td>
                  <td>{row.subject}</td>
                  <td>{row.teacher || '—'}</td>
                  <td className="gp-num">{row.grade}</td>
                  <td>{row.remarks}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>No released grades are available for this report.</td>
              </tr>
            )}
          </tbody>
          {report.overall_average ? (
            <tfoot>
              <tr>
                <td colSpan={3}>Average of the grades shown</td>
                <td className="gp-num">{report.overall_average}</td>
                <td />
              </tr>
            </tfoot>
          ) : null}
        </table>

        <p className="gp-note">Passing grade: {report.passing_score}. Only grades released by the school are included.</p>
        <PrintFooter generatedAt={report.generated_at} />
      </article>
    </div>
  );
}
