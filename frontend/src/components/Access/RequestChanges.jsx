import { useState } from 'react';
import { fileUrl } from '../../services/api';
import './RequestChanges.css';

const PHOTO = /\.(jpe?g|png|webp|gif)$/i;

function Value({ value }) {
  if (value === null || value === undefined || value === '') return <span className="rc-empty">—</span>;
  if (PHOTO.test(value)) return <img className="rc-photo" src={fileUrl(value)} alt="" loading="lazy" />;
  return <span className="rc-text">{value}</span>;
}

// "See changes": what a request changes, field by field, as it stood when it was submitted.
export default function RequestChanges({ changes }) {
  const [open, setOpen] = useState(false);
  if (!changes?.length) return null;
  return (
    <div className="rc">
      <button type="button" className="rc-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? 'Hide changes' : `See changes (${changes.length})`}
      </button>
      {open ? (
        <div className="rc-wrap">
          <table className="rc-table">
            <thead>
              <tr>
                <th>What</th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((row, index) => (
                <tr key={`${row.label}-${index}`}>
                  <th scope="row">{row.label}</th>
                  <td>
                    <Value value={row.before} />
                  </td>
                  <td className="rc-after">
                    <Value value={row.after} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
