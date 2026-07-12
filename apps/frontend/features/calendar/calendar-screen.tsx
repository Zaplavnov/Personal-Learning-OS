"use client";

import { CalendarDays, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { ApiClientError, backendApi, type CalendarItem, type CalendarItemStatus } from "@/lib/api/client";

const statusLabels: Record<CalendarItemStatus, string> = { planned: "Запланировано", in_progress: "В процессе", completed: "Завершено", skipped: "Пропущено" };

export function CalendarScreen() {
  const [items, setItems] = useState<CalendarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const range = useMemo(() => { const start = new Date(); start.setHours(0, 0, 0, 0); const end = new Date(start); end.setDate(end.getDate() + 7); return { start, end }; }, []);
  const load = useCallback(async () => { try { setItems(await backendApi.listCalendar(range.start.toISOString(), range.end.toISOString())); setError(null); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось загрузить календарь"); } finally { setLoading(false); } }, [range]);
  useEffect(() => { const controller = new AbortController(); backendApi.listCalendar(range.start.toISOString(), range.end.toISOString(), controller.signal).then((result) => { setItems(result); setError(null); }).catch((requestError: unknown) => { if (!controller.signal.aborted) setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось загрузить календарь"); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [range]);
  async function recalculate() { setRecalculating(true); try { await backendApi.recalculateCalendar(45); await load(); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось перестроить план"); } finally { setRecalculating(false); } }
  async function updateStatus(item: CalendarItem, status: CalendarItemStatus) { try { const updated = await backendApi.updateCalendarItem(item.id, { status }); setItems((current) => current.map((entry) => entry.id === item.id ? updated : entry)); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось обновить действие"); } }
  const days = Array.from({ length: 7 }, (_, index) => { const date = new Date(range.start); date.setDate(date.getDate() + index); return date; });
  return <>
    <PageHead eyebrow="Детерминированный план без бесконечного долга" title="Календарь" action={<button className="primary" onClick={() => void recalculate()} disabled={recalculating} type="button"><RefreshCw />{recalculating ? "Перестраиваем…" : "Пересчитать 45 мин"}</button>} />
    {error && <p className="inline-error">{error}</p>}
    {loading ? <section className="card state-card"><span className="state-loader" /><h2>Загружаем неделю…</h2></section> : items.length === 0 ? <section className="card state-card"><span className="round-icon blue"><CalendarDays /></span><h2>План пока пуст</h2><p>Пересчитай календарь — scheduler уложит самые полезные действия в 45 минут.</p><button className="primary" onClick={() => void recalculate()} type="button">Сформировать план</button></section> : <section className="week card real-calendar"><div className="week-head">{days.map((day) => <span className={day.toDateString() === new Date().toDateString() ? "today" : ""} key={day.toISOString()}>{new Intl.DateTimeFormat("ru-RU", { weekday: "short", day: "numeric" }).format(day)}</span>)}</div><div className="week-body">{days.map((day) => { const dayItems = items.filter((item) => item.planned_start && new Date(item.planned_start).toDateString() === day.toDateString()); return <div className="day" key={day.toISOString()}>{dayItems.map((item) => <article className={`calendar-event ${item.item_type}`} key={item.id}><small>{item.planned_start ? new Date(item.planned_start).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }) : "Гибко"} · {item.estimated_minutes} мин</small><b>{item.title}</b><p>{item.rationale}</p><select aria-label={`Статус: ${item.title}`} value={item.status} onChange={(event) => void updateStatus(item, event.target.value as CalendarItemStatus)}>{Object.entries(statusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></article>)}</div>; })}</div></section>}
    <section className="calendar-note card"><RefreshCw /><div><h3>Почему план изменился?</h3><p>Каждая версия сохраняет budget, выбранные источники, приоритеты и rationale. Flexible-действия прошлого расчёта помечаются skipped, если перестали попадать в лимит.</p></div></section>
  </>;
}
