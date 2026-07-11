"use client";

import {
  ArrowRight, BookOpen, ChevronRight, CircleHelp, Clock3, Flag,
  ListChecks, Play, RefreshCw, Search, ShieldCheck, Target,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { Skill } from "@/components/ui/skill";
import { backendApi } from "@/lib/api/client";

function Metric({ icon, value, label, tone }: { icon: React.ReactNode; value: string; label: string; tone: string }) {
  return <div className="metric"><span className={`round-icon ${tone}`}>{icon}</span><div><strong>{value}</strong><span>{label}</span></div></div>;
}

export function TodayScreen() {
  const [dueReviews, setDueReviews] = useState<number | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    backendApi.listDueReviews(controller.signal).then((items) => setDueReviews(items.length)).catch(() => undefined);
    return () => controller.abort();
  }, []);

  return <>
    <PageHead eyebrow="26 мая, понедельник" title="Сегодня" action={<button className="search-button" type="button"><Search /> Быстрый поиск <kbd>⌘ K</kbd></button>} />
    <Link className="space-chip" href="/spaces"><BookOpen /> Линейная алгебра <ChevronRight /></Link>
    <section className="goal-banner"><span className="round-icon blue"><Target /></span><div><span>Текущая цель</span><strong>Понять геометрический смысл линейных преобразований</strong></div><Link className="link-button" href="/spaces">Открыть маршрут <ArrowRight /></Link></section>
    <div className="today-grid">
      <section className="card focus-card">
        <div className="focus-copy"><p className="accent-label">Главное действие</p><h2>Повторить ключевые концепции</h2><span className="time"><Clock3 />По due date</span><p className="muted">Укрепит объяснение и применение</p><Link className="primary" href="/reviews"><Play />Начать повторение</Link></div>
        <div className="vector-visual" aria-label="Схема линейного преобразования"><div className="plane"><i /><i /><i /><i /></div><span className="axis x" /><span className="axis y" /><span className="vector one" /><span className="vector two" /></div>
      </section>
      <section className="card boundary"><div className="card-title"><h3>Граница понимания</h3><CircleHelp /></div><Skill label="Воспроизведение" state="уверенно" value={82} tone="good" /><Skill label="Объяснение" state="требует внимания" value={38} tone="warn" /><Skill label="Применение" state="слабо" value={18} tone="weak" /></section>
    </div>
    <section className="metrics card"><Metric icon={<RefreshCw />} value={dueReviews === null ? "…" : String(dueReviews)} label="повторения по due date" tone="blue" /><Metric icon={<Flag />} value="2" label="пробела" tone="amber" /><Metric icon={<ShieldCheck />} value="67%" label="устойчивости" tone="sage" /></section>
    <Link className="next-card card" href="/spaces"><span className="round-icon blue"><ListChecks /></span><span><small>Далее в пространстве</small><strong>Ортогональные преобразования</strong><em>Исследуем сохранение длины и углов</em></span><ChevronRight /></Link>
  </>;
}
