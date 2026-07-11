"use client";

import { ArrowLeft, BrainCircuit, CalendarPlus, Plus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type Concept,
  type ConceptState,
  type EvidenceType,
  type KnowledgeDimension,
  type ReviewType,
} from "@/lib/api/client";

const dimensions: { key: KnowledgeDimension; label: string }[] = [
  { key: "recall", label: "Воспроизведение" },
  { key: "explanation", label: "Объяснение" },
  { key: "structure", label: "Структура" },
  { key: "comparison", label: "Сравнение" },
  { key: "application", label: "Применение" },
  { key: "hypothesis_generation", label: "Гипотезы" },
  { key: "stability", label: "Устойчивость" },
];

const evidenceLabels: Record<EvidenceType, string> = {
  viewed: "Просмотрено",
  note_created: "Создана заметка",
  user_explanation: "Самостоятельное объяснение",
  review_answer: "Ответ на повторении",
  task_solved: "Решена задача",
  applied_in_project: "Применено в проекте",
  manual_adjustment: "Ручная корректировка",
};

function message(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}

export function ConceptDetailScreen({ conceptId }: { conceptId: string }) {
  const [concept, setConcept] = useState<Concept | null>(null);
  const [state, setState] = useState<ConceptState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [nextConcept, nextState] = await Promise.all([
        backendApi.getConcept(conceptId),
        backendApi.getConceptState(conceptId),
      ]);
      setConcept(nextConcept);
      setState(nextState);
      setError(null);
    } catch (requestError) {
      setError(message(requestError, "Не удалось загрузить состояние концепции"));
    } finally {
      setLoading(false);
    }
  }, [conceptId]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      backendApi.getConcept(conceptId, controller.signal),
      backendApi.getConceptState(conceptId, controller.signal),
    ])
      .then(([nextConcept, nextState]) => {
        setConcept(nextConcept);
        setState(nextState);
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(message(requestError, "Не удалось загрузить состояние концепции"));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [conceptId]);

  if (loading) return <section className="card state-card"><span className="state-loader" /><h2>Собираем evidence…</h2></section>;
  if (error || !concept || !state) return <section className="card state-card"><h2>Состояние недоступно</h2><p>{error}</p><button className="secondary" onClick={() => void load()} type="button">Повторить</button></section>;

  return <>
    <Link className="back-link" href="/graph"><ArrowLeft /> К карте знаний</Link>
    <PageHead eyebrow={`${state.evidence_count} свидетельств · confidence ${Math.round(state.confidence * 100)}%`} title={concept.title} action={<div className="head-actions"><button className="secondary" onClick={() => setEvidenceOpen(true)} type="button"><Plus /> Evidence</button><button className="primary" onClick={() => setReviewOpen(true)} type="button"><CalendarPlus /> Повторение</button></div>} />
    <p className="concept-lead">{concept.description ?? "Описание концепции пока не добавлено."}</p>
    <div className="knowledge-state-layout">
      <section className="card knowledge-dimensions">
        <div className="card-title"><div><p className="accent-label">Knowledge State v0</p><h2>Граница понимания</h2></div><BrainCircuit /></div>
        {dimensions.map(({ key, label }) => <div className="dimension-row" key={key}><div><span>{label}</span><b>{Math.round(state[key])}%</b></div><div className="skill-track"><i style={{ width: `${state[key]}%` }} /></div></div>)}
        <div className="confidence-note"><strong>Уверенность расчёта: {Math.round(state.confidence * 100)}%</strong><p>Confidence отражает объём и силу evidence, а не уровень знания. Слабые действия вроде просмотра почти не меняют оценку.</p></div>
      </section>
      <section className="card evidence-timeline">
        <div className="card-title"><div><p className="accent-label">Прозрачный расчёт</p><h2>Почему система так считает</h2></div></div>
        {state.recent_evidence.length === 0 ? <div className="notes-empty"><span>∅</span><p>Evidence пока нет. Добавь наблюдение или пройди повторение.</p></div> : state.recent_evidence.map((item) => <article key={item.id}><div><b>{evidenceLabels[item.evidence_type]}</b><time>{new Date(item.occurred_at).toLocaleString("ru-RU")}</time></div><p>{dimensions.find((entry) => entry.key === item.dimension)?.label}: {item.score_delta > 0 ? "+" : ""}{item.score_delta} × {item.strength.toFixed(2)}</p><small>Источник: {item.source_type}</small></article>)}
        <p className="next-review">Следующее повторение: {state.next_review_at ? new Date(state.next_review_at).toLocaleString("ru-RU") : "не запланировано"}</p>
      </section>
    </div>
    {evidenceOpen && <EvidenceModal conceptId={conceptId} onClose={() => setEvidenceOpen(false)} onSaved={(next) => { setEvidenceOpen(false); setState((current) => current ? { ...current, ...next } : current); void load(); }} />}
    {reviewOpen && <ReviewCreateModal concept={concept} onClose={() => setReviewOpen(false)} onSaved={() => setReviewOpen(false)} />}
  </>;
}

function EvidenceModal({ conceptId, onClose, onSaved }: { conceptId: string; onClose: () => void; onSaved: (state: ConceptState) => void }) {
  const [dimension, setDimension] = useState<KnowledgeDimension>("recall");
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("manual_adjustment");
  const [delta, setDelta] = useState(10);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); try { const result = await backendApi.createConceptEvidence(conceptId, { evidence_type: evidenceType, dimension, score_delta: delta, strength: null, source_type: "concept_detail", metadata: {} }); onSaved(result.state); } catch (requestError) { setError(message(requestError, "Не удалось сохранить evidence")); } }
  return <div className="modal-wrap" onClick={onClose}><form className="review-modal entity-form" onClick={(event) => event.stopPropagation()} onSubmit={submit}><p className="accent-label">Новое evidence</p><h2>Зафиксировать наблюдение</h2><label>Тип<select value={evidenceType} onChange={(event) => setEvidenceType(event.target.value as EvidenceType)}>{Object.entries(evidenceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Измерение<select value={dimension} onChange={(event) => setDimension(event.target.value as KnowledgeDimension)}>{dimensions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label><label>Изменение<input type="number" min={-100} max={100} value={delta} onChange={(event) => setDelta(Number(event.target.value))} /></label>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button className="secondary" onClick={onClose} type="button">Отмена</button><button className="primary" type="submit">Сохранить</button></div></form></div>;
}

function ReviewCreateModal({ concept, onClose, onSaved }: { concept: Concept; onClose: () => void; onSaved: () => void }) {
  const [reviewType, setReviewType] = useState<ReviewType>("explain");
  const [prompt, setPrompt] = useState(`Объясни своими словами: ${concept.title}`);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); try { await backendApi.createReviewItem({ concept_id: concept.id, review_type: reviewType, prompt, expected_points: [] }); onSaved(); } catch (requestError) { setError(message(requestError, "Не удалось создать повторение")); } }
  return <div className="modal-wrap" onClick={onClose}><form className="review-modal entity-form" onClick={(event) => event.stopPropagation()} onSubmit={submit}><p className="accent-label">Ручной prompt</p><h2>Запланировать повторение</h2><label>Формат<select value={reviewType} onChange={(event) => setReviewType(event.target.value as ReviewType)}><option value="recall">Воспроизвести</option><option value="explain">Объяснить</option><option value="compare">Сравнить</option><option value="apply">Применить</option><option value="structure">Встроить в структуру</option></select></label><label>Вопрос<textarea required value={prompt} onChange={(event) => setPrompt(event.target.value)} /></label>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button className="secondary" onClick={onClose} type="button">Отмена</button><button className="primary" type="submit">Добавить в очередь</button></div></form></div>;
}
