import LineMark from '../../../components/LineMark/LineMark';

export default function FieldLabel({ children, icon = 'cms' }) {
  return (
    <span className="desk-line">
      <LineMark name={icon} size={14} />
      {children}
    </span>
  );
}
