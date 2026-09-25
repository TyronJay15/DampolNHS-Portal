import Icon from '../Icon/Icon';

export default function LineMark({ name, size = 16 }) {
  return (
    <span className="line-mark">
      <Icon name={name} size={size} />
    </span>
  );
}
