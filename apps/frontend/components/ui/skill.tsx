export function Skill({
  label,
  state,
  value,
  tone,
}: {
  label: string;
  state?: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="skill">
      <p><b>{label}</b>{state && <span> — {state}</span>}</p>
      <div className="bar"><i className={tone} style={{ width: `${value}%` }} /></div>
    </div>
  );
}
