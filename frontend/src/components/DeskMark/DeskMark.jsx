import Icon from '../Icon/Icon';

export default function DeskMark({ name, size = 16 }) {
  return (
    <span className={`desk-mark${size < 18 ? ' is-sm' : ''}`}>
      <Icon name={name} size={size} />
    </span>
  );
}
