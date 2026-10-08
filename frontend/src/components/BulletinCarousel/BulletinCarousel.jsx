import { useEffect, useRef, useState } from 'react';
import { fileUrl } from '../../services/api';
import { formatEventWhen, textPreview } from '../../utils/textPreview';
import './BulletinCarousel.css';

const STEP = 380;
const SWIPE = 50;

function wrapOffset(index, active, total) {
  let offset = ((index - active) % total + total) % total;
  if (offset > total / 2) offset -= total;
  return offset;
}

export default function BulletinCarousel({ items, onOpen }) {
  const [active, setActive] = useState(0);
  const [dragX, setDragX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const drag = useRef(null);
  const skipClick = useRef(false);
  const total = items.length;
  const canSpin = total > 1;

  useEffect(() => {
    if (!canSpin || dragging) return undefined;
    const id = window.setInterval(() => setActive((value) => (value + 1) % total), 5000);
    return () => window.clearInterval(id);
  }, [active, canSpin, dragging, total]);

  function go(step) {
    if (!canSpin) return;
    setActive((value) => (value + step + total) % total);
  }

  function onPointerDown(event) {
    if (!canSpin || event.target.closest('.lp-read-full')) return;
    drag.current = { x: event.clientX, moved: false };
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (!drag.current) return;
    const dx = event.clientX - drag.current.x;
    if (Math.abs(dx) > 8) drag.current.moved = true;
    setDragX(dx);
  }

  function onPointerUp() {
    if (!drag.current) return;
    const dx = dragX;
    const moved = drag.current.moved;
    drag.current = null;
    setDragging(false);
    setDragX(0);
    if (moved) skipClick.current = true;
    if (dx <= -SWIPE) go(1);
    else if (dx >= SWIPE) go(-1);
  }

  function openOrSelect(item, index, center) {
    if (skipClick.current) {
      skipClick.current = false;
      return;
    }
    if (center) onOpen(item);
    else setActive(index);
  }

  return (
    <div className="lp-car">
      <div
        className={`lp-car-stage${dragging ? ' is-dragging' : ''}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        {items.map((item, index) => {
          const offset = wrapOffset(index, active, total);
          const preview = textPreview(item.body);
          const center = offset === 0;
          const eventWhen = item.kind === 'event' ? formatEventWhen(item) : '';
          const far = Math.abs(offset) > 2;
          return (
            <article
              key={item.id}
              className={`lp-car-card${center ? ' is-center' : ''}`}
              style={{
                zIndex: 20 - Math.abs(offset),
                opacity: far ? 0 : 1 - Math.abs(offset) * 0.38,
                pointerEvents: far ? 'none' : 'auto',
                transform: `translateX(${offset * STEP + dragX}px) scale(${1 - Math.abs(offset) * 0.16})`,
              }}
              aria-hidden={far || undefined}
            >
              <button
                type="button"
                className="lp-car-photo"
                onClick={() => openOrSelect(item, index, center)}
                aria-label={center ? `Read ${item.title}` : `Show ${item.title}`}
              >
                {item.image ? <img src={fileUrl(item.image)} alt="" draggable="false" /> : <span>{eventWhen ? 'Event' : 'News'}</span>}
              </button>
              <div className="lp-car-bar" />
              <p className="lp-car-tag">{eventWhen || item.category || 'News'}</p>
              <h3 className="lp-car-title">{item.title}</h3>
              <p className="lp-car-desc">{preview.text}</p>
              {center ? (
                <button type="button" className="lp-read-full" onClick={() => onOpen(item)}>
                  Read full
                </button>
              ) : null}
            </article>
          );
        })}
      </div>
      {canSpin ? (
        <>
          <button type="button" className="lp-car-arrow is-left" onClick={() => go(-1)} aria-label="Previous announcement">
            ‹
          </button>
          <button type="button" className="lp-car-arrow is-right" onClick={() => go(1)} aria-label="Next announcement">
            ›
          </button>
        </>
      ) : null}
    </div>
  );
}
