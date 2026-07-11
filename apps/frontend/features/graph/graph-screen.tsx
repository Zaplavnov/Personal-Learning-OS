"use client";

import { ArrowRight, Plus, Search } from "lucide-react";
import { useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { Skill } from "@/components/ui/skill";
import { concepts } from "@/lib/mock-data";

export function GraphScreen() {
  const [selected, setSelected] = useState(2);
  return <>
    <PageHead eyebrow="37 концепций · 52 связи" title="Карта знаний" action={<div className="head-actions"><button className="secondary" type="button"><Search /> Найти концепцию</button><button className="primary" type="button"><Plus /> Концепция</button></div>} />
    <div className="graph-layout"><section className="knowledge-canvas card">{concepts.map((concept, index) => <button key={concept[0]} onClick={() => setSelected(index)} className={`concept-node n${index} ${concept[2]} ${selected === index ? "selected" : ""}`} type="button"><span>{concept[0]}</span><small>{concept[1]}</small></button>)}<div className="edge e1" /><div className="edge e2" /><div className="edge e3" /><div className="edge e4" /></section>
      <aside className="concept-panel card"><span className="status-pill">В работе</span><h2>{concepts[selected][0]}</h2><p>Направление, которое после линейного преобразования сохраняется, меняя только масштаб.</p><div className="mini-stats"><div><strong>5</strong><span>связей</span></div><div><strong>3</strong><span>источника</span></div><div><strong>2</strong><span>пробела</span></div></div><h4>Состояние понимания</h4><Skill label="Воспроизведение" value={82} tone="good" /><Skill label="Объяснение" value={38} tone="warn" /><button className="primary full" type="button">Открыть концепцию <ArrowRight /></button></aside>
    </div>
  </>;
}
