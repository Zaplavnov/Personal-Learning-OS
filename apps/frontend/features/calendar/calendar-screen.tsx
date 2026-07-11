import { Plus, RefreshCw } from "lucide-react";
import { PageHead } from "@/components/ui/page-head";
import { weekDays } from "@/lib/mock-data";

function Event({ time, title, tone }: { time: string; title: string; tone: string }) {
  return <div className={`event ${tone}`}><small>{time}</small><b>{title}</b></div>;
}

export function CalendarScreen() {
  return <>
    <PageHead eyebrow="Адаптивный план" title="Май 2026" action={<button className="primary" type="button"><Plus /> Запланировать</button>} />
    <section className="week card"><div className="week-head">{weekDays.map((day, index) => <span className={index === 1 ? "today" : ""} key={day}>{day}</span>)}</div><div className="week-body">{weekDays.map((day, index) => <div className="day" key={day}>{index === 1 && <><Event time="09:30" title="Повторение · собственные векторы" tone="blue" /><Event time="19:00" title="Лекция 7 · ортогональность" tone="sage" /></>}{index === 3 && <Event time="18:30" title="Практика · 3 задачи" tone="amber" />}{index === 5 && <Event time="11:00" title="Глубокая сессия · 60 мин" tone="blue" />}</div>)}</div></section>
    <section className="calendar-note card"><RefreshCw /><div><h3>План адаптируется к реальному темпу</h3><p>Если ты пропустишь занятие или задержишься на теме, маршрут перестроится без накопления «долгов».</p></div><button className="secondary" type="button">Как это работает</button></section>
  </>;
}
