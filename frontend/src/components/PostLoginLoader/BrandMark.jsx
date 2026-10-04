import { fileUrl } from '../../services/api';

/** The school seal on its round disc with the green ring, shared by the sign-in and sign-out overlays. */
export default function BrandMark({ logo, onReady }) {
  return (
    <div className="pll-mark">
      <svg className="pll-ring" viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="50" r="49" pathLength="100" />
      </svg>
      <div className="pll-disc">
        {logo ? <img className="pll-logo" src={fileUrl(logo)} alt="" onLoad={onReady} onError={onReady} /> : null}
      </div>
    </div>
  );
}
