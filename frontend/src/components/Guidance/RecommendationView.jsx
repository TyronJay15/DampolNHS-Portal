import { Link } from 'react-router-dom';
import MatchCard from './MatchCard';
import MatchLabel from './MatchLabel';

// The saved recommendation: primary programs as cards, then "Explore More Programs".
// programPath links each program to its page (students); advisers pass none.
export default function RecommendationView({ recommendation, programPath, compare }) {
  if (!recommendation.ready) {
    return <p className="card gd-panel gd-note">{recommendation.not_ready}</p>;
  }
  const { primary, additional, families } = recommendation;
  return (
    <>
      {recommendation.notice ? (
        <p className="gd-notice" role="status">
          {recommendation.notice}
        </p>
      ) : null}
      {families.length ? (
        <div className="gd-families">
          <span>Strongest program families</span>
          {families.slice(0, 3).map((family, index) => (
            <span key={family} className={`gd-family-chip${index === 0 ? ' is-first' : ''}`}>
              {family}
            </span>
          ))}
        </div>
      ) : null}
      <section className="gd-primary" aria-label="Your top programs">
        {primary.map((item) => (
          <MatchCard key={item.program.code} item={item} programPath={programPath} compare={compare} />
        ))}
      </section>
      {additional.length ? (
        <section className="desk" aria-label="Explore more programs">
          <div className="gd-section-head">
            <h2>Explore More Programs</h2>
            <p>Lower fit on the evidence available, not a verdict on your future.</p>
          </div>
          <div className="gd-explore">
            {additional.map((item) => {
              const content = (
                <>
                  <strong>
                    {item.rank}. {item.program.name}
                  </strong>
                  <small>{item.program.family}</small>
                  <MatchLabel label={item.label} />
                  {item.explanation[0] ? <small>{item.explanation[0]}</small> : null}
                </>
              );
              return programPath ? (
                <Link key={item.program.code} className="gd-mini" to={`${programPath}/${item.program.code}`}>
                  {content}
                </Link>
              ) : (
                <div key={item.program.code} className="gd-mini">
                  {content}
                </div>
              );
            })}
          </div>
        </section>
      ) : (
        <p className="gd-note">Only the strongest matches are shown because the evidence for more programs is thin.</p>
      )}
    </>
  );
}
