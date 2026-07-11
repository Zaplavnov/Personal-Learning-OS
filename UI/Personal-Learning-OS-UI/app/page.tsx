"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight, BookOpen, Bot, BrainCircuit, CalendarDays, ChevronRight,
  CircleHelp, Clock3, FileText, Flag, Folder, Home, Link2, ListChecks,
  Menu, Moon, Network, Play, Plus, RefreshCw, Search, ShieldCheck,
  Sparkles, Sun, Target, X
} from "lucide-react";

type Page = "today" | "spaces" | "graph" | "materials" | "calendar" | "tutor";

const nav = [
  { id: "today" as Page, label: "Сегодня", icon: Home },
  { id: "spaces" as Page, label: "Пространства", icon: Folder },
  { id: "graph" as Page, label: "Карта знаний", icon: Network },
  { id: "materials" as Page, label: "Материалы", icon: FileText },
  { id: "calendar" as Page, label: "Календарь", icon: CalendarDays },
  { id: "tutor" as Page, label: "AI-наставник", icon: Bot },
];

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const stored = localStorage.getItem("plos-theme");
    const value = stored ? stored === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = value ? "dark" : "light";
    const frame = requestAnimationFrame(() => setDark(value));
    return () => cancelAnimationFrame(frame);
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("plos-theme", next ? "dark" : "light");
  };
  return <button className="icon-button theme-toggle" onClick={toggle} aria-label="Переключить тему">{dark ? <Sun /> : <Moon />}</button>;
}

function Shell({ page, setPage, children }: { page: Page; setPage: (p: Page) => void; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return <div className="app-shell">
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand"><span className="brand-mark"><BrainCircuit /></span><span>Personal Learning OS</span></div>
      <nav>{nav.map(({ id, label, icon: Icon }) => <button key={id} className={page === id ? "active" : ""} onClick={() => { setPage(id); setOpen(false); }}><Icon /><span>{label}</span></button>)}</nav>
      <div className="sidebar-foot">
        <div className="sync"><span className="online" /> Obsidian синхронизирован</div>
        <div className="profile"><div className="avatar">Д</div><div><b>Дмитрий</b><span>Личное пространство</span></div><ThemeToggle /></div>
      </div>
    </aside>
    <button className="mobile-menu icon-button" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
    <main className="main">{children}</main>
  </div>;
}

function PageHead({ eyebrow, title, action }: { eyebrow: string; title: string; action?: React.ReactNode }) {
  return <header className="page-head"><div><p>{eyebrow}</p><h1>{title}</h1></div>{action}</header>;
}

function Today({ setPage }: { setPage: (p: Page) => void }) {
  const [review, setReview] = useState(false);
  return <>
    <PageHead eyebrow="26 мая, понедельник" title="Сегодня" action={<button className="search-button"><Search /> Быстрый поиск <kbd>⌘ K</kbd></button>} />
    <button className="space-chip" onClick={() => setPage("spaces")}><BookOpen /> Линейная алгебра <ChevronRight /></button>
    <section className="goal-banner"><span className="round-icon blue"><Target /></span><div><span>Текущая цель</span><strong>Понять геометрический смысл линейных преобразований</strong></div><button className="link-button" onClick={() => setPage("spaces")}>Открыть маршрут <ArrowRight /></button></section>
    <div className="today-grid">
      <section className="card focus-card">
        <div className="focus-copy"><p className="accent-label">Главное действие</p><h2>Повторить: собственные значения и собственные векторы</h2><span className="time"><Clock3 />18 минут</span><p className="muted">Укрепит объяснение и применение</p><button className="primary" onClick={() => setReview(true)}><Play />Начать повторение</button></div>
        <div className="vector-visual" aria-label="Схема линейного преобразования"><div className="plane"><i /><i /><i /><i /></div><span className="axis x" /><span className="axis y" /><span className="vector one" /><span className="vector two" /></div>
      </section>
      <section className="card boundary"><div className="card-title"><h3>Граница понимания</h3><CircleHelp /></div>
        <Skill label="Воспроизведение" state="уверенно" value={82} tone="good" />
        <Skill label="Объяснение" state="требует внимания" value={38} tone="warn" />
        <Skill label="Применение" state="слабо" value={18} tone="weak" />
      </section>
    </div>
    <section className="metrics card"><Metric icon={<RefreshCw />} value="4" label="повторения" tone="blue"/><Metric icon={<Flag />} value="2" label="пробела" tone="amber"/><Metric icon={<ShieldCheck />} value="67%" label="устойчивости" tone="sage"/></section>
    <button className="next-card card" onClick={() => setPage("spaces")}><span className="round-icon blue"><ListChecks /></span><span><small>Далее в пространстве</small><strong>Ортогональные преобразования</strong><em>Исследуем сохранение длины и углов</em></span><ChevronRight /></button>
    {review && <div className="modal-wrap" onClick={() => setReview(false)}><div className="review-modal" onClick={e => e.stopPropagation()}><button className="close icon-button" onClick={() => setReview(false)}><X /></button><span className="round-icon blue"><RefreshCw /></span><p className="accent-label">Повторение · вопрос 1 из 4</p><h2>Объясни своими словами: почему собственный вектор не меняет направление при линейном преобразовании?</h2><textarea placeholder="Сформулируй ответ без подсказки…" autoFocus /><div className="modal-actions"><button className="secondary" onClick={() => setReview(false)}>Отложить</button><button className="primary">Проверить ответ <ArrowRight /></button></div></div></div>}
  </>;
}

function Skill({ label, state, value, tone }: { label: string; state: string; value: number; tone: string }) { return <div className="skill"><p><b>{label}</b><span>— {state}</span></p><div className="bar"><i className={tone} style={{ width: `${value}%` }} /></div></div>; }
function Metric({ icon, value, label, tone }: { icon: React.ReactNode; value: string; label: string; tone: string }) { return <div className="metric"><span className={`round-icon ${tone}`}>{icon}</span><div><strong>{value}</strong><span>{label}</span></div></div>; }

const concepts = [
  ["Линейное преобразование", "уверенно", "mastered"], ["Матрица преобразования", "устойчиво", "mastered"],
  ["Собственные векторы", "в работе", "active"], ["Собственные значения", "в работе", "active"],
  ["Диагонализация", "есть пробел", "gap"], ["Ортогональность", "следующее", "next"],
  ["PCA", "не изучено", "locked"],
];

function Spaces() { return <><PageHead eyebrow="Учебное пространство" title="Линейная алгебра" action={<button className="primary"><Plus /> Добавить материал</button>} />
  <section className="space-hero card"><div><p className="accent-label">Текущая цель</p><h2>Понять геометрический смысл линейных преобразований</h2><p className="muted">Связать формальные определения с визуальной интуицией и применением в машинном обучении.</p></div><div className="ring"><strong>67%</strong><span>устойчивость</span></div></section>
  <div className="section-heading"><div><h2>Учебный маршрут</h2><p>План меняется вместе с твоим пониманием</p></div><button className="secondary">Настроить маршрут</button></div>
  <section className="path-list">{[["Завершено","Линейные преобразования как функции","6 концепций"],["Сейчас","Собственные значения и собственные векторы","4 из 7 действий"],["Далее","Ортогональные преобразования","примерно 2 часа"],["Позже","Диагонализация и PCA","зависит от 3 концепций"]].map((x,i)=><article className={`path-item card p${i}`} key={x[1]}><span className="path-index">{i<1?"✓":i+1}</span><div><small>{x[0]}</small><h3>{x[1]}</h3><p>{x[2]}</p></div><ChevronRight /></article>)}</section>
  </>; }

function Graph() { const [selected,setSelected]=useState(2); return <><PageHead eyebrow="37 концепций · 52 связи" title="Карта знаний" action={<div className="head-actions"><button className="secondary"><Search /> Найти концепцию</button><button className="primary"><Plus /> Концепция</button></div>} />
  <div className="graph-layout"><section className="knowledge-canvas card">{concepts.map((c,i)=><button key={c[0]} onClick={()=>setSelected(i)} className={`concept-node n${i} ${c[2]} ${selected===i?"selected":""}`}><span>{c[0]}</span><small>{c[1]}</small></button>)}<div className="edge e1"/><div className="edge e2"/><div className="edge e3"/><div className="edge e4"/></section>
  <aside className="concept-panel card"><span className="status-pill">В работе</span><h2>{concepts[selected][0]}</h2><p>Направление, которое после линейного преобразования сохраняется, меняя только масштаб.</p><div className="mini-stats"><div><strong>5</strong><span>связей</span></div><div><strong>3</strong><span>источника</span></div><div><strong>2</strong><span>пробела</span></div></div><h4>Состояние понимания</h4><Skill label="Воспроизведение" state="" value={82} tone="good"/><Skill label="Объяснение" state="" value={38} tone="warn"/><button className="primary full">Открыть концепцию <ArrowRight /></button></aside></div></>; }

function Materials() { return <><PageHead eyebrow="18 источников" title="Материалы" action={<button className="primary"><Plus /> Добавить материал</button>} /><div className="filters"><button className="active">Все</button><button>Курсы</button><button>Видео</button><button>Статьи</button><button>Книги</button></div><section className="material-grid">{[
  ["Курс","Essence of Linear Algebra","3Blue1Brown","8 из 16 глав","61%"], ["Книга","Linear Algebra Done Right","Sheldon Axler","Глава 5","34%"], ["Видео","Eigenvectors and eigenvalues","MIT OpenCourseWare","Следующий фрагмент: 18:42","18%"], ["Notebook","Линейные преобразования в Python","Собственная практика","4 задачи","75%"], ["Статья","A geometric understanding of matrices","Better Explained","12 минут","0%"], ["Заметки","Конспекты по линалу","Obsidian","24 заметки","—"]
  ].map((m,i)=><article className="material card" key={m[1]}><div className={`material-cover c${i}`}><BookOpen /></div><div><small>{m[0]}</small><h3>{m[1]}</h3><p>{m[2]}</p><div className="material-meta"><span>{m[3]}</span><b>{m[4]}</b></div></div></article>)}</section></>; }

function CalendarPage() { return <><PageHead eyebrow="Адаптивный план" title="Май 2026" action={<button className="primary"><Plus /> Запланировать</button>} /><section className="week card"><div className="week-head">{["Пн 25","Вт 26","Ср 27","Чт 28","Пт 29","Сб 30","Вс 31"].map((d,i)=><span className={i===1?"today":""} key={d}>{d}</span>)}</div><div className="week-body">{[0,1,2,3,4,5,6].map(day=><div className="day" key={day}>{day===1&&<><Event time="09:30" title="Повторение · собственные векторы" tone="blue"/><Event time="19:00" title="Лекция 7 · ортогональность" tone="sage"/></>}{day===3&&<Event time="18:30" title="Практика · 3 задачи" tone="amber"/>}{day===5&&<Event time="11:00" title="Глубокая сессия · 60 мин" tone="blue"/>}</div>)}</div></section><section className="calendar-note card"><RefreshCw/><div><h3>План адаптируется к реальному темпу</h3><p>Если ты пропустишь занятие или задержишься на теме, маршрут перестроится без накопления «долгов».</p></div><button className="secondary">Как это работает</button></section></>; }
function Event({time,title,tone}:{time:string;title:string;tone:string}) { return <div className={`event ${tone}`}><small>{time}</small><b>{title}</b></div>; }

function Tutor() { const [sent,setSent]=useState(false); return <><PageHead eyebrow="Знает твои материалы и историю обучения" title="AI-наставник" /><section className="tutor-layout"><div className="chat card"><div className="chat-start"><span className="round-icon blue"><Sparkles /></span><h2>О чём хочешь подумать?</h2><p>Я могу помочь разобраться, но сначала попрошу тебя сформулировать собственную модель.</p><div className="suggestions"><button>Разобрать мой пробел в диагонализации</button><button>Проверить моё объяснение собственных векторов</button><button>Связать тему с применением в ML</button></div>{sent&&<div className="message"><b>Ты</b><p>Помоги мне проверить понимание собственных векторов.</p></div>}</div><div className="composer"><textarea placeholder="Задай вопрос или вставь своё объяснение…"/><button className="primary" onClick={()=>setSent(true)}><ArrowRight /></button></div></div><aside className="tutor-context"><section className="card"><h3><Link2 />Контекст диалога</h3><p>Линейная алгебра</p><span>4 концепции</span><span>3 заметки</span><span>2 прошлые ошибки</span></section><section className="card tutor-rule"><ShieldCheck/><h3>AI помогает думать</h3><p>Ответ наставника не считается доказательством твоего знания. Сначала — собственная попытка.</p></section></aside></section></>; }

export default function HomePage() {
  const [page, setPage] = useState<Page>("today");
  return <Shell page={page} setPage={setPage}>{page === "today" && <Today setPage={setPage}/>} {page === "spaces" && <Spaces/>} {page === "graph" && <Graph/>} {page === "materials" && <Materials/>} {page === "calendar" && <CalendarPage/>} {page === "tutor" && <Tutor/>}</Shell>;
}
