import { Link } from 'react-router-dom';
import DeskMark from '../DeskMark/DeskMark';
import { useCms } from '../../hooks/useCms';
import { DEFAULT_CMS } from '../../utils/cmsDefaults';

export default function PublicLinks() {
  const cms = useCms();
  const facebook =
    cms?.footer?.facebookUrl || cms?.contact?.facebook_url || DEFAULT_CMS.footer.facebookUrl;

  return (
    <article className="card desk-tile">
      <h2 className="desk-title">
        <DeskMark name="home" size={16} />
        School links
      </h2>
      <nav className="desk-link-list">
        <Link to="/">
          <DeskMark name="home" size={16} />
          Dampol website
        </Link>
        <a href={facebook} target="_blank" rel="noopener noreferrer">
          <DeskMark name="place" size={16} />
          Facebook page
        </a>
      </nav>
    </article>
  );
}
