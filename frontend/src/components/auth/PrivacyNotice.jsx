import { PRIVACY_NOTICE } from '../../data/privacyNotice';
import './PrivacyNotice.css';

export default function PrivacyNotice() {
  return (
    <div className="privacy-box">
      <h3>Data Privacy Act of 2012 (RA 10173)</h3>
      <div className="privacy-scroll">
        {PRIVACY_NOTICE.map((block) => (
          <p key={block.title}>
            <strong>{block.title}</strong> {block.body}
          </p>
        ))}
      </div>
    </div>
  );
}
