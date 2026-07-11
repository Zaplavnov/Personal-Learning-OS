"use client";

import {
  ArrowLeft,
  Clock3,
  ExternalLink,
  Play,
  Plus,
  Save,
  Square,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type MaterialDetail,
  type Note,
  type NoteType,
} from "@/lib/api/client";

const noteTypes: { value: NoteType; label: string }[] = [
  { value: "insight", label: "Мысль" },
  { value: "question", label: "Вопрос" },
  { value: "gap", label: "Пробел" },
  { value: "example", label: "Пример" },
  { value: "general", label: "Общее" },
];

function formatDuration(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds]
    .filter((_, index) => hours > 0 || index > 0)
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

function formatPosition(seconds: number | null) {
  if (seconds === null) return null;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

export function MaterialDetailScreen({ materialId }: { materialId: string }) {
  const [material, setMaterial] = useState<MaterialDetail | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startPosition, setStartPosition] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [noteType, setNoteType] = useState<NoteType>("insight");
  const [notePosition, setNotePosition] = useState("");
  const [reflection, setReflection] = useState("");
  const [endPosition, setEndPosition] = useState("");
  const [working, setWorking] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedMaterial, loadedNotes] = await Promise.all([
        backendApi.getMaterial(materialId),
        backendApi.listMaterialNotes(materialId),
      ]);
      setMaterial(loadedMaterial);
      setNotes(loadedNotes);
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось загрузить материал",
      );
    } finally {
      setLoading(false);
    }
  }, [materialId]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      backendApi.getMaterial(materialId, controller.signal),
      backendApi.listMaterialNotes(materialId, controller.signal),
    ])
      .then(([loadedMaterial, loadedNotes]) => {
        setMaterial(loadedMaterial);
        setNotes(loadedNotes);
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted)
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить материал",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [materialId]);

  useEffect(() => {
    const startedAt = material?.active_session?.started_at;
    if (!startedAt) return;
    const update = () =>
      setElapsed(
        Math.max(
          0,
          Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000),
        ),
      );
    update();
    const interval = window.setInterval(update, 1000);
    return () => window.clearInterval(interval);
  }, [material?.active_session?.started_at]);

  async function startSession() {
    if (!material) return;
    setWorking(true);
    setError(null);
    try {
      await backendApi.startLearningSession(
        material.id,
        startPosition ? Number(startPosition) : null,
      );
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось начать сессию",
      );
    } finally {
      setWorking(false);
    }
  }

  async function saveNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!material) return;
    setWorking(true);
    setError(null);
    try {
      const note = await backendApi.createNote({
        learning_space_id: material.learning_space_id,
        material_id: material.id,
        learning_session_id: material.active_session?.id ?? null,
        body: noteBody,
        source_position_seconds: notePosition ? Number(notePosition) : null,
        note_type: noteType,
      });
      setNotes((current) => [note, ...current]);
      setNoteBody("");
      setNotePosition("");
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось сохранить заметку",
      );
    } finally {
      setWorking(false);
    }
  }

  async function completeSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!material?.active_session) return;
    setWorking(true);
    setError(null);
    try {
      await backendApi.completeLearningSession(material.active_session.id, {
        end_position_seconds: endPosition ? Number(endPosition) : null,
        reflection: reflection || null,
      });
      setReflection("");
      setEndPosition("");
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось завершить сессию",
      );
    } finally {
      setWorking(false);
    }
  }

  if (loading)
    return (
      <section className="card state-card">
        <span className="state-loader" />
        <h2>Открываем материал…</h2>
      </section>
    );
  if (!material)
    return (
      <>
        <Link className="back-link" href="/materials">
          <ArrowLeft /> Все материалы
        </Link>
        <section className="card state-card error-state">
          <h2>Материал не найден</h2>
          <p>{error}</p>
          <button
            className="secondary"
            onClick={() => void load()}
            type="button"
          >
            Повторить
          </button>
        </section>
      </>
    );

  const isVideo = material.type === "video";
  return (
    <>
      <Link className="back-link" href="/materials">
        <ArrowLeft /> Все материалы
      </Link>
      <PageHead
        eyebrow={`${material.type} · ${material.status}`}
        title={material.title}
        action={
          material.url ? (
            <a
              className="secondary"
              href={material.url}
              target="_blank"
              rel="noreferrer"
            >
              Открыть источник <ExternalLink />
            </a>
          ) : undefined
        }
      />
      <section className="material-detail-grid">
        <div>
          <section className="card material-overview">
            <p className="muted">{material.author ?? "Автор не указан"}</p>
            <p>{material.description ?? "Описание пока не добавлено."}</p>
            {material.estimated_minutes && (
              <span className="time">
                <Clock3 />
                {material.estimated_minutes} минут
              </span>
            )}
          </section>
          <section className="card session-card">
            {material.active_session ? (
              <>
                <div className="session-live">
                  <span className="online" />
                  <div>
                    <small>Учебная сессия идёт</small>
                    <strong>{formatDuration(elapsed)}</strong>
                  </div>
                </div>
                <form className="completion-form" onSubmit={completeSession}>
                  <label>
                    Короткая reflection
                    <textarea
                      value={reflection}
                      onChange={(event) => setReflection(event.target.value)}
                      placeholder="Что стало понятнее? Где остался вопрос?"
                    />
                  </label>
                  {isVideo && (
                    <label>
                      Позиция завершения, сек
                      <input
                        min="0"
                        type="number"
                        value={endPosition}
                        onChange={(event) => setEndPosition(event.target.value)}
                      />
                    </label>
                  )}
                  <button className="primary" disabled={working} type="submit">
                    <Square /> Завершить сессию
                  </button>
                </form>
              </>
            ) : (
              <>
                <p className="accent-label">Учебная сессия</p>
                <h2>Начни сфокусированную работу</h2>
                <p className="muted">
                  Время и заметки будут связаны с этим материалом.
                </p>
                {isVideo && (
                  <label className="position-field">
                    Стартовая позиция, сек
                    <input
                      min="0"
                      type="number"
                      value={startPosition}
                      onChange={(event) => setStartPosition(event.target.value)}
                    />
                  </label>
                )}
                <button
                  className="primary"
                  disabled={working}
                  onClick={() => void startSession()}
                  type="button"
                >
                  <Play /> Начать сессию
                </button>
              </>
            )}
          </section>
          <form className="card quick-note" onSubmit={saveNote}>
            <div className="card-title">
              <h3>Быстрая заметка</h3>
              <Plus />
            </div>
            <textarea
              value={noteBody}
              onChange={(event) => setNoteBody(event.target.value)}
              placeholder="Мысль, вопрос, пробел или пример…"
              required
            />
            <div className="note-controls">
              <select
                value={noteType}
                onChange={(event) =>
                  setNoteType(event.target.value as NoteType)
                }
              >
                {noteTypes.map((item) => (
                  <option value={item.value} key={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              {isVideo && (
                <input
                  min="0"
                  type="number"
                  value={notePosition}
                  onChange={(event) => setNotePosition(event.target.value)}
                  placeholder="Таймкод, сек"
                />
              )}
              <button className="primary" disabled={working} type="submit">
                <Save /> Сохранить
              </button>
            </div>
          </form>
        </div>
        <aside className="card notes-panel">
          <div className="card-title">
            <h3>Заметки</h3>
            <span>{notes.length}</span>
          </div>
          {notes.length === 0 ? (
            <div className="notes-empty">
              <p>Заметок пока нет.</p>
              <span>Зафиксируй первую мысль во время изучения.</span>
            </div>
          ) : (
            <div className="notes-list">
              {notes.map((note) => (
                <article key={note.id}>
                  <div>
                    <span className={`status-pill ${note.note_type}`}>
                      {
                        noteTypes.find((item) => item.value === note.note_type)
                          ?.label
                      }
                    </span>
                    {note.source_position_seconds !== null && (
                      <small>
                        {formatPosition(note.source_position_seconds)}
                      </small>
                    )}
                  </div>
                  <p>{note.body}</p>
                  <time>
                    {new Date(note.created_at).toLocaleString("ru-RU")}
                  </time>
                </article>
              ))}
            </div>
          )}
        </aside>
      </section>
      {error && <p className="inline-error">{error}</p>}
    </>
  );
}
