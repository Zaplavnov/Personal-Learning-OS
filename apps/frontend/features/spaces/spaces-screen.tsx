"use client";

import { ArrowRight, FolderOpen, Plus, Target, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type LearningSpace,
} from "@/lib/api/client";

export function SpacesScreen() {
  const [spaces, setSpaces] = useState<LearningSpace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const loadSpaces = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      setSpaces(await backendApi.listLearningSpaces(signal));
    } catch (requestError) {
      if (!signal?.aborted) {
        setError(
          requestError instanceof ApiClientError
            ? requestError.message
            : "Не удалось загрузить пространства",
        );
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    backendApi
      .listLearningSpaces(controller.signal)
      .then(setSpaces)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить пространства",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <>
      <PageHead
        eyebrow={
          loading
            ? "Загружаем пространства"
            : `${spaces.length} учебных пространств`
        }
        title="Пространства"
        action={
          <button
            className="primary"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus /> Создать пространство
          </button>
        }
      />
      {loading && (
        <section className="card state-card">
          <span className="state-loader" />
          <h2>Собираем учебную картину…</h2>
          <p>Загружаем пространства и их текущие цели.</p>
        </section>
      )}
      {!loading && error && (
        <section className="card state-card error-state">
          <h2>Не удалось открыть пространства</h2>
          <p>{error}</p>
          <button
            className="secondary"
            onClick={() => void loadSpaces()}
            type="button"
          >
            Повторить
          </button>
        </section>
      )}
      {!loading && !error && spaces.length === 0 && (
        <section className="card state-card">
          <span className="round-icon blue">
            <FolderOpen />
          </span>
          <h2>Первое пространство ждёт</h2>
          <p>
            Создай долгосрочную область обучения, а затем добавь конкретную
            цель.
          </p>
          <button
            className="primary"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus /> Создать пространство
          </button>
        </section>
      )}
      {!loading && !error && spaces.length > 0 && (
        <section className="spaces-grid">
          {spaces.map((space) => {
            const activeGoal = space.goals.find(
              (goal) => goal.status === "active",
            );
            return (
              <Link
                className="space-card card"
                href={`/spaces/${space.id}`}
                key={space.id}
              >
                <span
                  className="space-color"
                  style={{ background: space.color ?? "var(--blue)" }}
                />
                <div className="space-card-head">
                  <small>
                    {space.status === "active"
                      ? "Активное пространство"
                      : "Архив"}
                  </small>
                  <strong>{space.goals.length} целей</strong>
                </div>
                <h2>{space.title}</h2>
                <p>{space.description ?? "Описание пока не добавлено."}</p>
                <div className="active-goal-line">
                  <Target />
                  <span>
                    <small>Текущая цель</small>
                    <b>{activeGoal?.title ?? "Не выбрана"}</b>
                  </span>
                </div>
                <span className="space-open">
                  Открыть пространство <ArrowRight />
                </span>
              </Link>
            );
          })}
        </section>
      )}
      {creating && (
        <CreateSpaceModal
          onClose={() => setCreating(false)}
          onCreated={(space) => {
            setSpaces((current) => [...current, space]);
            setCreating(false);
          }}
        />
      )}
    </>
  );
}

function CreateSpaceModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (space: LearningSpace) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onCreated(
        await backendApi.createLearningSpace({
          title,
          description: description || null,
          color: "#5f7894",
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось создать пространство",
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
        <p className="accent-label">Новое пространство</p>
        <h2>Что ты хочешь изучать долго?</h2>
        <label>
          Название
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Например, Теория вероятностей"
            required
            autoFocus
          />
        </label>
        <label>
          Описание
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Контекст и направление обучения…"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary" disabled={saving} type="submit">
            {saving ? "Создаём…" : "Создать"}
          </button>
        </div>
      </form>
    </div>
  );
}
