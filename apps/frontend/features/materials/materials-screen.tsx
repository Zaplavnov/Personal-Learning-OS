import { BookOpen, Plus } from "lucide-react";
import { PageHead } from "@/components/ui/page-head";
import { materials } from "@/lib/mock-data";

export function MaterialsScreen() {
  return <>
    <PageHead eyebrow="18 источников" title="Материалы" action={<button className="primary" type="button"><Plus /> Добавить материал</button>} />
    <div className="filters"><button className="active" type="button">Все</button><button type="button">Курсы</button><button type="button">Видео</button><button type="button">Статьи</button><button type="button">Книги</button></div>
    <section className="material-grid">{materials.map((material, index) => <article className="material card" key={material[1]}><div className={`material-cover c${index}`}><BookOpen /></div><div><small>{material[0]}</small><h3>{material[1]}</h3><p>{material[2]}</p><div className="material-meta"><span>{material[3]}</span><b>{material[4]}</b></div></div></article>)}</section>
  </>;
}
