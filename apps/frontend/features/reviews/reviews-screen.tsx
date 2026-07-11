"use client";

import { ArrowRight, CalendarClock, RefreshCw } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { ApiClientError, backendApi, type ConceptState, type ReviewItem, type ReviewResult } from "@/lib/api/client";

export function ReviewsScreen() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [current, setCurrent] = useState<ReviewItem | null>(null);
  const [lastState, setLastState] = useState<ConceptState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    backendApi.listDueReviews(controller.signal).then((next) => { setItems(next); setError(null); }).catch((requestError: unknown) => { if (!controller.signal.aborted) setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось загрузить очередь"); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  async function skip(item: ReviewItem) { try { await backendApi.skipReview(item.id); setItems((all) => all.filter((entry) => entry.id !== item.id)); setCurrent(null); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось пропустить повторение"); } }
  async function reschedule(item: ReviewItem) { const due = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(); try { await backendApi.rescheduleReview(item.id, due); setItems((all) => all.filter((entry) => entry.id !== item.id)); setCurrent(null); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось перенести повторение"); } }
  return <>
    <PageHead eyebrow={loading ? "Загружаем очередь" : `${items.length} к повторению`} title="Повторения" action={items.length > 0 ? <button className="primary" onClick={() => setCurrent(items[0])} type="button"><RefreshCw /> Начать сессию</button> : undefined} />
    {error && <p className="inline-error">{error}</p>}
    {lastState && <section className="goal-banner"><span className="round-icon blue"><RefreshCw /></span><div><span>State обновлён без перезагрузки</span><strong>Измерение и stability пересчитаны · confidence {Math.round(lastState.confidence * 100)}%</strong></div><Link className="link-button" href={`/concepts/${lastState.concept_id}`}>Посмотреть состояние <ArrowRight /></Link></section>}
    {loading ? <section className="card state-card"><span className="state-loader" /><h2>Проверяем due date…</h2></section> : items.length === 0 ? <section className="card state-card"><span className="round-icon sage"><CalendarClock /></span><h2>На сегодня всё</h2><p>Новые элементы появятся здесь в назначенный момент. Вопрос можно создать на странице концепции.</p><Link className="secondary" href="/graph">Открыть карту знаний</Link></section> : <section className="review-queue">{items.map((item, index) => <article className="card review-queue-item" key={item.id}><span className="queue-number">{index + 1}</span><div><small>{item.review_type} · {new Date(item.due_at).toLocaleString("ru-RU")}</small><h2>{item.prompt}</h2></div><button className="secondary" onClick={() => setCurrent(item)} type="button">Ответить <ArrowRight /></button></article>)}</section>}
    {current && <ReviewSession item={current} onClose={() => setCurrent(null)} onSkip={() => void skip(current)} onReschedule={() => void reschedule(current)} onSubmitted={(state) => { setItems((all) => all.filter((entry) => entry.id !== current.id)); setLastState(state); setCurrent(null); }} />}
  </>;
}

function ReviewSession({ item, onClose, onSkip, onReschedule, onSubmitted }: { item: ReviewItem; onClose: () => void; onSkip: () => void; onReschedule: () => void; onSubmitted: (state: ConceptState) => void }) {
  const [answer, setAnswer] = useState("");
  const [rating, setRating] = useState(3);
  const [result, setResult] = useState<ReviewResult>("partial");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { const response = await backendApi.submitReviewAttempt(item.id, { answer, self_rating: rating, result }); onSubmitted(response.state); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось сохранить ответ"); setSaving(false); } }
  return <div className="modal-wrap" onClick={onClose}><form className="review-modal review-session" onClick={(event) => event.stopPropagation()} onSubmit={submit}><span className="round-icon blue"><RefreshCw /></span><p className="accent-label">Повторение · самооценка без LLM</p><h2>{item.prompt}</h2><textarea required placeholder="Сформулируй ответ без подсказки…" value={answer} onChange={(event) => setAnswer(event.target.value)} autoFocus />{item.expected_points.length > 0 && <div className="expected-points"><b>Ожидаемые пункты</b>{item.expected_points.map((point) => <span key={point}>• {point}</span>)}</div>}<div className="review-rating"><label>Насколько уверенно? <strong>{rating}/5</strong><input type="range" min="1" max="5" value={rating} onChange={(event) => setRating(Number(event.target.value))} /></label><label>Результат<select value={result} onChange={(event) => setResult(event.target.value as ReviewResult)}><option value="failed">Не получилось</option><option value="partial">Частично</option><option value="passed">Получилось</option></select></label></div>{error && <p className="form-error">{error}</p>}<div className="review-secondary-actions"><button type="button" onClick={onSkip}>Пропустить</button><button type="button" onClick={onReschedule}>Завтра</button></div><div className="modal-actions"><button className="secondary" onClick={onClose} type="button">Закрыть</button><button className="primary" disabled={saving} type="submit">{saving ? "Сохраняем…" : "Сохранить ответ"} <ArrowRight /></button></div></form></div>;
}
