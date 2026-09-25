import { useRef, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import { fileUrl } from '../../../services/api';
import { deleteCmsPhoto, uploadCmsPhoto } from '../../../services/cmsService';

function isUpload(url) {
  return String(url || '').includes('/media/cms/');
}

export default function CmsPhotoField({ label, value, fallback = '', onChange }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      if (isUpload(value)) await deleteCmsPhoto(value).catch(() => {});
      const data = await uploadCmsPhoto(file);
      onChange(data.url);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError('');
    try {
      if (isUpload(value)) await deleteCmsPhoto(value).catch(() => {});
      onChange('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cms-photo">
      {label ? (
        <span className="cms-photo-label desk-line">
          <LineMark name="cms" size={14} />
          {label}
        </span>
      ) : null}
      <div className={`cms-photo-frame${value ? '' : ' is-empty'}`}>
        {value ? <img src={fileUrl(value)} alt="" /> : <p>No photo yet</p>}
        <div className="cms-photo-tools">
          <button type="button" className="btn" disabled={busy} onClick={() => inputRef.current?.click()}>
            {busy ? 'Working…' : value ? 'Replace' : 'Upload'}
          </button>
          {value ? (
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={remove}>
              Remove
            </button>
          ) : null}
          {fallback && value !== fallback ? (
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onChange(fallback)}>
              Default
            </button>
          ) : null}
        </div>
      </div>
      {error ? <p className="form-error">{error}</p> : null}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        hidden
        onChange={onFile}
      />
    </div>
  );
}
