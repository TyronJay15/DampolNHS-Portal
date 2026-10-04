// Progress through a multi-step form. steps: [{ id, label }]; the page styles it through className.
export default function StepTrail({ steps, current, className }) {
  const index = steps.findIndex((step) => step.id === current);
  return (
    <ol className={className} aria-label="Progress">
      {steps.map((step, position) => (
        <li
          key={step.id}
          className={position === index ? 'is-active' : position < index ? 'is-done' : ''}
          aria-current={position === index ? 'step' : undefined}
        >
          {step.label}
        </li>
      ))}
    </ol>
  );
}
