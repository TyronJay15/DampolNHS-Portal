import { useEffect } from 'react';
import { fileUrl } from '../../services/api';
import { formatPostedOn } from '../../utils/textPreview';
import './AnnouncementReader.css';

export default function AnnouncementReader({ item, onClose }) {
  useEffect(() => {
    if (!item) return undefined;
    function onKey(event) {
      if (event.key === 'Escape') onClose();
    }
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener('keydown', onKey);
    };
  }, [item, onClose]);

  if (!item) return null;

  return (
    <div className="announce-reader" role="presentation" onClick={onClose}>
      <div
        className="announce-reader-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="announce-reader-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="announce-reader-bar">
          <p className="announce-reader-meta">
            {item.category ? <span>{item.category}</span> : null}
            {item.published_at ? <time>{formatPostedOn(item.published_at)}</time> : null}
          </p>
          <button type="button" className="announce-reader-close" onClick={onClose}>
            Close
          </button>
        </div>
        {item.image ? <img src={fileUrl(item.image)} alt="" className="announce-reader-photo" /> : null}
        <h2 id="announce-reader-title">{item.title}</h2>
        <p className="announce-reader-body">{item.body}</p>
      </div>
    </div>
  );
}
