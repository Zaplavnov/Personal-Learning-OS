import { ChevronRight, Plus } from "lucide-react";
import { PageHead } from "@/components/ui/page-head";
import { learningPath } from "@/lib/mock-data";

export function SpacesScreen() {
  return <>
    <PageHead eyebrow="Учебное пространство" title="Линейная алгебра" action={<button className="primary" type="button"><Plus /> Добавить материал</button>} />
    <section className="space-hero card"><div><p className="accent-label">Текущая цель</p><h2>Понять геометрический смысл линейных преобразований</h2><p className="muted">Связать формальные определения с визуальной интуицией и применением в машинном обучении.</p></div><div className="ring"><strong>67%</strong><span>устойчивость</span></div></section>
    <div className="section-heading"><div><h2>Учебный маршрут</h2><p>План меняется вместе с твоим пониманием</p></div><button className="secondary" type="button">Настроить маршрут</button></div>
    <section className="path-list">{learningPath.map((item, index) => <article className={`path-item card p${index}`} key={item[1]}><span className="path-index">{index < 1 ? "✓" : index + 1}</span><div><small>{item[0]}</small><h3>{item[1]}</h3><p>{item[2]}</p></div><ChevronRight /></article>)}</section>
  </>;
}
