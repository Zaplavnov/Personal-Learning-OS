"use client";

import { ArrowLeft, Check, CirclePause, Network, Plus, Target, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type LearningGoal,
  type Concept,
  type LearningPath,
  type LearningSpace,
} from "@/lib/api/client";

const goalStatusLabels = {
  active: "Текущая",
  paused: "На паузе",
  completed: "Завершена",
};

export function SpaceDetailScreen({ spaceId }: { spaceId: string }) {
  const [space, setSpace] = useState<LearningSpace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingGoal, setCreatingGoal] = useState(false);
  const [activatingGoalId, setActivatingGoalId] = useState<string | null>(null);

  const loadSpace = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        setSpace(await backendApi.getLearningSpace(spaceId, signal));
      } catch (requestError) {
        if (!signal?.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить пространство",
          );
        }
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [spaceId],
  );

  useEffect(() => {
    const controller = new AbortController();
    backendApi
      .getLearningSpace(spaceId, controller.signal)
      .then(setSpace)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить пространство",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [spaceId]);

  async function activateGoal(goal: LearningGoal) {
    setActivatingGoalId(goal.id);
    setError(null);
    try {
      await backendApi.activateLearningGoal(goal.id);
      await loadSpace();
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось активировать цель",
      );
    } finally {
      setActivatingGoalId(null);
    }
  }

  if (loading) {
    return (
      <section className="card state-card">
        <span className="state-loader" />
        <h2>Открываем пространство…</h2>
      </section>
    );
  }

  if (!space) {
    return (
      <>
        <Link className="back-link" href="/spaces">
          <ArrowLeft /> Все пространства
        </Link>
        <section className="card state-card error-state">
          <h2>Пространство не найдено</h2>
          <p>{error}</p>
          <button
            className="secondary"
            onClick={() => void loadSpace()}
            type="button"
          >
            Повторить
          </button>
        </section>
      </>
    );
  }

  const activeGoal = space.goals.find((goal) => goal.status === "active");

  return (
    <>
      <Link className="back-link" href="/spaces">
        <ArrowLeft /> Все пространства
      </Link>
      <PageHead
        eyebrow={`${space.goals.length} целей · ${space.status === "active" ? "активное" : "архив"}`}
        title={space.title}
        action={
          <button
            className="primary"
            onClick={() => setCreatingGoal(true)}
            type="button"
          >
            <Plus /> Добавить цель
          </button>
        }
      />
      <section className="space-hero card detail-hero">
        <span
          className="space-color large"
          style={{ background: space.color ?? "var(--blue)" }}
        />
        <div>
          <p className="accent-label">Долгосрочная область обучения</p>
          <p className="muted">
            {space.description ?? "Описание пока не добавлено."}
          </p>
        </div>
      </section>
      {activeGoal && (
        <section className="goal-banner">
          <span className="round-icon blue">
            <Target />
          </span>
          <div>
            <span>Текущая цель</span>
            <strong>{activeGoal.title}</strong>
            {activeGoal.description && <small>{activeGoal.description}</small>}
          </div>
        </section>
      )}
      {!activeGoal && (
        <section className="card no-active-goal">
          <CirclePause />
          <div>
            <h3>Текущая цель не выбрана</h3>
            <p>Активируй одну из целей или создай новую.</p>
          </div>
        </section>
      )}
      {error && <p className="inline-error">{error}</p>}
      <div className="section-heading">
        <div>
          <h2>Цели пространства</h2>
          <p>Одновременно активна только одна цель</p>
        </div>
      </div>
      {space.goals.length === 0 ? (
        <section className="card state-card compact">
          <h2>Добавь первую конкретную цель</h2>
          <p>Она превратит направление обучения в проверяемый результат.</p>
          <button
            className="primary"
            onClick={() => setCreatingGoal(true)}
            type="button"
          >
            <Plus /> Добавить цель
          </button>
        </section>
      ) : (
        <section className="goals-list">
          {space.goals.map((goal) => (
            <article className={`goal-card card ${goal.status}`} key={goal.id}>
              <div className="goal-card-top">
                <span className={`status-pill ${goal.status}`}>
                  {goalStatusLabels[goal.status]}
                </span>
                <small>Приоритет {goal.priority}</small>
              </div>
              <h3>{goal.title}</h3>
              <p>{goal.description ?? "Описание пока не добавлено."}</p>
              {goal.target_date && (
                <small>
                  Целевая дата:{" "}
                  {new Date(goal.target_date).toLocaleDateString("ru-RU")}
                </small>
              )}
              <div className="goal-actions">
                <GoalPathAction goal={goal} spaceId={space.id} />
                {goal.status === "active" ? (
                  <span className="active-marker">
                    <Check /> Активная цель
                  </span>
                ) : (
                  <button
                    className="secondary"
                    disabled={activatingGoalId === goal.id}
                    onClick={() => void activateGoal(goal)}
                    type="button"
                  >
                    {activatingGoalId === goal.id
                      ? "Активируем…"
                      : "Сделать текущей"}
                  </button>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
      {creatingGoal && (
        <CreateGoalModal
          spaceId={space.id}
          onClose={() => setCreatingGoal(false)}
          onCreated={async () => {
            setCreatingGoal(false);
            await loadSpace();
          }}
        />
      )}
    </>
  );
}

function GoalPathAction({ goal, spaceId }: { goal: LearningGoal; spaceId: string }) {
  const [path, setPath] = useState<LearningPath | null>(null);
  const [creating, setCreating] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    backendApi.getGoalPath(goal.id, controller.signal).then(setPath).catch(() => undefined);
    return () => controller.abort();
  }, [goal.id]);
  if (path) return <Link className="secondary" href={`/spaces/${spaceId}/paths/${path.id}`}><Network /> Открыть путь</Link>;
  return <><button className="secondary" onClick={() => setCreating(true)} type="button"><Network /> Построить путь</button>{creating && <GeneratePathModal goal={goal} spaceId={spaceId} onClose={() => setCreating(false)} onCreated={setPath} />}</>;
}

function GeneratePathModal({ goal, spaceId, onClose, onCreated }: { goal: LearningGoal; spaceId: string; onClose: () => void; onCreated: (path: LearningPath) => void }) {
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    backendApi.listConcepts(spaceId, controller.signal).then((items) => { setConcepts(items); if (items[0]) setSelected([items[0].id]); }).catch((requestError: unknown) => { if (!controller.signal.aborted) setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось загрузить концепции"); });
    return () => controller.abort();
  }, [spaceId]);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { const detail = await backendApi.generateLearningPath(goal.id, { target_concept_ids: selected, max_depth: 4 }); onCreated(detail.path); } catch (requestError) { setError(requestError instanceof ApiClientError ? requestError.message : "Не удалось построить draft"); setSaving(false); } }
  return <div className="modal-wrap" onClick={onClose}><form className="review-modal entity-form" onClick={(event) => event.stopPropagation()} onSubmit={submit}><button className="close icon-button" onClick={onClose} type="button"><X /></button><p className="accent-label">Rule-based planner v0</p><h2>Целевые концепции пути</h2><p className="muted">Prerequisites добавятся автоматически, но draft останется под твоим контролем.</p><div className="concept-picker">{concepts.map((concept) => <label key={concept.id}><input type="checkbox" checked={selected.includes(concept.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, concept.id] : current.filter((id) => id !== concept.id))} />{concept.title}</label>)}</div>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button className="secondary" onClick={onClose} type="button">Отмена</button><button className="primary" disabled={saving || selected.length === 0} type="submit">{saving ? "Строим…" : "Создать draft"}</button></div></form></div>;
}

function CreateGoalModal({
  spaceId,
  onClose,
  onCreated,
}: {
  spaceId: string;
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(50);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await backendApi.createLearningGoal(spaceId, {
        title,
        description: description || null,
        priority,
        status: "paused",
      });
      await onCreated();
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось создать цель",
      );
      setSaving(false);
    }
  }

  return (
    <div className="modal-wrap" onClick={onClose}>
      <form
        className="review-modal entity-form"
        onClick={(event) => event.stopPropagation()}
        onSubmit={submit}
      >
        <button
          className="close icon-button"
          onClick={onClose}
          aria-label="Закрыть"
          type="button"
        >
          <X />
        </button>
        <p className="accent-label">Новая цель</p>
        <h2>Какой конкретный результат нужен?</h2>
        <label>
          Формулировка
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Например, научиться применять теорему Байеса"
            required
            autoFocus
          />
        </label>
        <label>
          Описание
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Ожидаемый результат и контекст…"
          />
        </label>
        <label>
          Приоритет
          <input
            min="0"
            type="number"
            value={priority}
            onChange={(event) => setPriority(Number(event.target.value))}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary" disabled={saving} type="submit">
            {saving ? "Создаём…" : "Создать цель"}
          </button>
        </div>
      </form>
    </div>
  );
}
