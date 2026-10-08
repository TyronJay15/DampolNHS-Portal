import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PublicLayout from './PublicLayout';
import Loading from '../../components/Loading/Loading';
import AnnouncementReader from '../../components/AnnouncementReader/AnnouncementReader';
import { MegaphoneIcon } from '../../components/icons/SchoolIcons';
import { fetchPublicBulletin } from '../../services/publicService';
import { fileUrl } from '../../services/api';
import { formatEventWhen, formatPostedOn, textPreview } from '../../utils/textPreview';
import './AnnouncementsPage.css';

export default function AnnouncementsPage() {
  const [items, setItems] = useState([]);
  const [openItem, setOpenItem] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPublicBulletin()
      .then((rows) => setItems(rows))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PublicLayout>
      <div className="announcements public-page public-section lp-container">
        <header className="public-hero">
          <h1>School news</h1>
          <p className="public-hero-kicker">Campus updates</p>
          <p>News and upcoming events appear here after they are published.</p>
        </header>
        {loading ? <Loading /> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        {!loading && !error && items.length === 0 ? (
          <div className="announcement-empty">
            <MegaphoneIcon />
            <h2>No announcements yet</h2>
            <p>There is nothing posted at the moment. Please check back later, or contact the school office if you need something specific.</p>
            <Link className="btn btn-secondary" to="/contact">
              Contact the school
            </Link>
          </div>
        ) : null}
        {items.length ? (
          <ul className="announcement-grid">
            {items.map((item) => {
              const preview = textPreview(item.body);
              return (
                <li key={item.id}>
                  <article className="card lift-card announcement-card">
                    {item.image ? <img src={fileUrl(item.image)} alt="" className="announcement-photo" /> : null}
                    <div className="announcement-copy">
                      <p className="announcement-meta">
                        {item.kind === 'event' && formatEventWhen(item) ? (
                          <time>{formatEventWhen(item, { long: true })}</time>
                        ) : null}
                        {item.category ? <span className="announcement-category">{item.category}</span> : null}
                        {item.kind !== 'event' && item.published_at ? <time>{formatPostedOn(item.published_at)}</time> : null}
                      </p>
                      <h2>{item.title}</h2>
                      <p>{preview.text}</p>
                      <button className="btn btn-secondary" type="button" onClick={() => setOpenItem(item)}>
                        Read full
                      </button>
                    </div>
                  </article>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
      <AnnouncementReader item={openItem} onClose={() => setOpenItem(null)} />
    </PublicLayout>
  );
}
