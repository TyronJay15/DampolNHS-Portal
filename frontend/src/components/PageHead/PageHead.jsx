import DeskMark from '../DeskMark/DeskMark';

export default function PageHead({ kicker, title, icon, children }) {
  return (
    <header className="desk-pagehead">
      {kicker ? <p className="desk-kicker">{kicker}</p> : null}
      <h1 className="desk-title">
        {icon ? <DeskMark name={icon} size={16} /> : null}
        {title}
      </h1>
      {children}
    </header>
  );
}
