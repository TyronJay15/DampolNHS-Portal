import './Loading.css';

export default function Loading({ label = 'Loading…' }) {
  return <p className="loading">{label}</p>;
}
