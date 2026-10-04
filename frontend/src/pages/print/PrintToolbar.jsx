import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const PDF_OPTIONS = {
  margin: 10,
  image: { type: 'jpeg', quality: 0.96 },
  html2canvas: { scale: 2, backgroundColor: '#ffffff' },
  jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  pagebreak: { mode: ['css', 'legacy'], avoid: ['tr', '.gp-info div', '.gp-group h3'] },
};

// Screen-only controls above a printable sheet: back, a term filter, Print, and a direct PDF download.
// The PDF library is loaded only when someone saves, so it never slows the rest of the app.
export default function PrintToolbar({ terms = [], fileName, sheetRef }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const term = params.get('term') || '';

  function pickTerm(value) {
    const next = new URLSearchParams(params);
    if (value) next.set('term', value);
    else next.delete('term');
    setParams(next, { replace: true });
  }

  async function saveAsPdf() {
    if (!sheetRef.current) return;
    setSaving(true);
    setError('');
    try {
      const { default: html2pdf } = await import('html2pdf.js');
      await html2pdf()
        .set({ ...PDF_OPTIONS, filename: `${fileName}.pdf` })
        .from(sheetRef.current)
        .save();
    } catch {
      setError('The PDF could not be created. Use Print and choose “Save as PDF” instead.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="gp-toolbar no-print">
      <button className="btn btn-secondary" type="button" onClick={() => navigate(-1)}>
        Back
      </button>
      <div className="gp-toolbar-actions">
        {terms.length ? (
          <select aria-label="Term" value={term} disabled={saving} onChange={(event) => pickTerm(event.target.value)}>
            <option value="">All terms</option>
            {terms.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </select>
        ) : null}
        <button className="btn btn-secondary" type="button" disabled={saving} onClick={() => window.print()}>
          Print
        </button>
        <button className="btn" type="button" disabled={saving} onClick={saveAsPdf}>
          {saving ? 'Saving PDF…' : 'Save as PDF'}
        </button>
      </div>
      {error ? <p className="gp-toolbar-error">{error}</p> : null}
    </div>
  );
}
