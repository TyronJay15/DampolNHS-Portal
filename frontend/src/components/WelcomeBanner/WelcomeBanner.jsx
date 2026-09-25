import { fileUrl } from '../../services/api';
import { useCms } from '../../hooks/useCms';
import { campusPhoto } from '../../utils/campusPhoto';

export default function WelcomeBanner({ children }) {
  const cms = useCms();
  const photo = campusPhoto(cms);
  const src = photo ? fileUrl(photo) : '';

  return (
    <header className={`dash-hero desk-banner${src ? ' has-photo' : ''}`}>
      {src ? <div className="desk-banner-photo" style={{ backgroundImage: `url("${src}")` }} aria-hidden="true" /> : null}
      <div className="desk-banner-copy">{children}</div>
    </header>
  );
}
