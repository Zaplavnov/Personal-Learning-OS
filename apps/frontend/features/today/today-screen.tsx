"use client";

import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  CircleHelp,
  Clock3,
  Flag,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
  Target,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { ApiClientError, backendApi, type TodayReadModel } from "@/lib/api/client";

const timeOptions = [15, 30, 45, 60, 90];

function Metric({ icon, value, label, tone }: { icon: React.ReactNode; value: string; label: string; tone: string }) {
  return <div className="metric"><span className={`round-icon ${tone}`}>{icon}</span><div><strong>{value}</strong><span>{label}</span></div></div>;
}

export function TodayScreen() {
  const [availableMinutes, setAvailableMinutes] = useState(45);
  const [today, setToday] = useState<TodayReadModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    backendApi.getToday(availableMinutes, controller.signal).then((result) => { setToday(result); setError(null); }).catch((requestError: unknown) => { if (!controller.signal.aborted) setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось построить план на сегодня"); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [availableMinutes]);

  const dateLabel = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
  if (loading && !today) return <section className="card state-card"><span className="state-loader" /><h2>Собираем следующий шаг…</h2></section>;
  if (error && !today) return <section className="card state-card"><h2>План недоступен</h2><p>{error}</p></section>;

  const primary = today?.primary_action;
  return <>
    <PageHead eyebrow={dateLabel} title="Сегодня" action={<div className="time-budget" aria-label="Доступное время">{timeOptions.map((minutes) => <button className={availableMinutes === minutes ? "active" : ""} onClick={() => setAvailableMinutes(minutes)} key={minutes} type="button">{minutes}</button>)}<span>мин</span></div>} />
    {today?.active_space && <Link className="space-chip" href={`/spaces/${today.active_space.id}`}><BookOpen /> {today.active_space.title} <ChevronRight /></Link>}
    {today?.active_goal && <section className="goal-banner"><span className="round-icon blue"><Target /></span><div><span>Текущая цель</span><strong>{today.active_goal.title}</strong></div><Link className="link-button" href={`/spaces/${today.active_space?.id}`}>Открыть маршрут <ArrowRight /></Link></section>}
    {!primary ? <Onboarding hasSpace={Boolean(today?.active_space)} /> : <>
      <div className="today-grid">
        <section className="card focus-card" data-testid="today-primary-action">
          <div className="focus-copy"><p className="accent-label">Что делать сейчас</p><h2 data-testid="today-primary-title">{primary.title}</h2><span className="time"><Clock3 />{primary.estimated_minutes} минут</span><p className="rationale"><CircleHelp />{primary.rationale}</p><p className="muted">Укрепит: <strong>{primary.target_dimension}</strong></p><Link className="primary" href={primary.action_url} data-testid="start-primary-action"><Play />Начать действие</Link></div>
          <div className="vector-visual" aria-label="Схема учебного действия"><div className="plane"><i /><i /><i /><i /></div><span className="axis x" /><span className="axis y" /><span className="vector one" /><span className="vector two" /></div>
        </section>
        <section className="card boundary"><div className="card-title"><h3>Состояние знания</h3><ShieldCheck /></div><div className="stability-value"><strong>{Math.round(today?.knowledge_stability.average ?? 0)}%</strong><span>средняя устойчивость</span></div><p>Confidence расчёта: {Math.round((today?.knowledge_stability.confidence ?? 0) * 100)}%</p><p>{today?.knowledge_stability.concept_count ?? 0} концепций с evidence</p></section>
      </div>
      <section className="metrics card"><Metric icon={<RefreshCw />} value={String(today?.due_review_count ?? 0)} label="due reviews" tone="blue" /><Metric icon={<Flag />} value={String(today?.open_gap_count ?? 0)} label="открытых gaps/questions" tone="amber" /><Metric icon={<Clock3 />} value={`${today?.scheduled_minutes ?? 0}/${availableMinutes}`} label="минут запланировано" tone="sage" /></section>
      {today && today.secondary_actions.length > 0 && <section className="secondary-plan"><div className="section-heading"><p className="accent-label">Если останется время</p><h2>Следующие действия</h2></div>{today.secondary_actions.map((action) => <Link className="next-card card" href={action.action_url} key={`${action.source_type}-${action.source_id}-${action.item_type}`}><span className="round-icon blue"><ListChecks /></span><span><small>{action.estimated_minutes} минут · укрепит {action.target_dimension}</small><strong>{action.title}</strong><em>{action.rationale}</em></span><ChevronRight /></Link>)}</section>}
    </>}
  </>;
}

function Onboarding({ hasSpace }: { hasSpace: boolean }) {
  return <section className="card state-card"><span className="round-icon blue"><Target /></span><h2>{hasSpace ? "Добавь первый материал" : "Создай учебное пространство"}</h2><p>{hasSpace ? "Scheduler предложит конкретное действие, когда появится активный материал." : "Определи область и активную цель — это станет контекстом ежедневного плана."}</p><Link className="primary" href={hasSpace ? "/materials" : "/spaces"}>{hasSpace ? "Добавить материал" : "Создать пространство"}<ArrowRight /></Link></section>;
}
