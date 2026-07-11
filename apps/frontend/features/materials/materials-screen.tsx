"use client";

import {
  BookOpen,
  FileText,
  FolderGit2,
  NotebookTabs,
  Play,
  Plus,
  X,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type LearningSpace,
  type Material,
  type MaterialType,
} from "@/lib/api/client";

const materialTypes: { value: MaterialType; label: string }[] = [
  { value: "video", label: "Видео" },
  { value: "article", label: "Статья" },
  { value: "book", label: "Книга / глава" },
  { value: "notebook", label: "Notebook" },
  { value: "repository", label: "Repository" },
  { value: "other", label: "Другое" },
];

function MaterialIcon({ type }: { type: MaterialType }) {
  if (type === "video") return <Play />;
  if (type === "article") return <FileText />;
  if (type === "notebook") return <NotebookTabs />;
  if (type === "repository") return <FolderGit2 />;
  return <BookOpen />;
}

export function MaterialsScreen() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [spaces, setSpaces] = useState<LearningSpace[]>([]);
  const [spaceFilter, setSpaceFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<MaterialType | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const loadMaterials = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMaterials(
        await backendApi.listMaterials({
          learningSpaceId: spaceFilter || undefined,
          type: typeFilter || undefined,
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось загрузить материалы",
      );
    } finally {
      setLoading(false);
    }
  }, [spaceFilter, typeFilter]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      backendApi.listMaterials(
        {
          learningSpaceId: spaceFilter || undefined,
          type: typeFilter || undefined,
        },
        controller.signal,
      ),
      backendApi.listLearningSpaces(controller.signal),
    ])
      .then(([loadedMaterials, loadedSpaces]) => {
        setMaterials(loadedMaterials);
        setSpaces(loadedSpaces);
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить материалы",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [spaceFilter, typeFilter]);

  return (
    <>
      <PageHead
        eyebrow={
          loading ? "Загружаем библиотеку" : `${materials.length} материалов`
        }
        title="Материалы"
        action={
          <button
            className="primary"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus /> Добавить материал
          </button>
        }
      />
      <div className="material-toolbar">
        <div className="filters">
          <button
            className={typeFilter === "" ? "active" : ""}
            onClick={() => setTypeFilter("")}
            type="button"
          >
            Все
          </button>
          {materialTypes.map((item) => (
            <button
              className={typeFilter === item.value ? "active" : ""}
              key={item.value}
              onClick={() => setTypeFilter(item.value)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
        <select
          aria-label="Фильтр по пространству"
          value={spaceFilter}
          onChange={(event) => setSpaceFilter(event.target.value)}
        >
          <option value="">Все пространства</option>
          {spaces.map((space) => (
            <option value={space.id} key={space.id}>
              {space.title}
            </option>
          ))}
        </select>
      </div>
      {loading && (
        <section className="card state-card">
          <span className="state-loader" />
          <h2>Открываем библиотеку…</h2>
        </section>
      )}
      {!loading && error && (
        <section className="card state-card error-state">
          <h2>Материалы недоступны</h2>
          <p>{error}</p>
          <button
            className="secondary"
            onClick={() => void loadMaterials()}
            type="button"
          >
            Повторить
          </button>
        </section>
      )}
      {!loading && !error && materials.length === 0 && (
        <section className="card state-card">
          <span className="round-icon blue">
            <BookOpen />
          </span>
          <h2>Добавь первый источник</h2>
          <p>
            Ссылка на видео, статью, книгу, notebook или repository станет
            началом учебной сессии.
          </p>
          <button
            className="primary"
            disabled={spaces.length === 0}
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus /> Добавить материал
          </button>
        </section>
      )}
      {!loading && !error && materials.length > 0 && (
        <section className="material-grid">
          {materials.map((material, index) => (
            <Link
              className="material card"
              href={`/materials/${material.id}`}
              key={material.id}
            >
              <div className={`material-cover c${index % 6}`}>
                <MaterialIcon type={material.type} />
              </div>
              <div>
                <small>
                  {
                    materialTypes.find((item) => item.value === material.type)
                      ?.label
                  }
                </small>
                <h3>{material.title}</h3>
                <p>{material.author ?? material.description ?? "Без автора"}</p>
                <div className="material-meta">
                  <span>
                    {material.estimated_minutes
                      ? `${material.estimated_minutes} мин`
                      : "Время не задано"}
                  </span>
                  <b>
                    {material.status === "completed" ? "Завершён" : "В работе"}
                  </b>
                </div>
              </div>
            </Link>
          ))}
        </section>
      )}
      {creating && (
        <CreateMaterialModal
          spaces={spaces}
          onClose={() => setCreating(false)}
          onCreated={(material) => {
            setMaterials((current) => [material, ...current]);
            setCreating(false);
          }}
        />
      )}
    </>
  );
}

function CreateMaterialModal({
  spaces,
  onClose,
  onCreated,
}: {
  spaces: LearningSpace[];
  onClose: () => void;
  onCreated: (material: Material) => void;
}) {
  const [spaceId, setSpaceId] = useState(spaces[0]?.id ?? "");
  const [type, setType] = useState<MaterialType>("video");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [author, setAuthor] = useState("");
  const [description, setDescription] = useState("");
  const [minutes, setMinutes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onCreated(
        await backendApi.createMaterial({
          learning_space_id: spaceId,
          type,
          title,
          url: url || null,
          author: author || null,
          description: description || null,
          estimated_minutes: minutes ? Number(minutes) : null,
          metadata: {},
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось создать материал",
      );
      setSaving(false);
    }
  }

  return (
    <div className="modal-wrap" onClick={onClose}>
      <form
        className="review-modal entity-form material-form"
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
        <p className="accent-label">Новый материал</p>
        <h2>Что будем изучать?</h2>
        {spaces.length === 0 ? (
          <p className="form-error">Сначала создай учебное пространство.</p>
        ) : (
          <>
            <div className="form-row">
              <label>
                Пространство
                <select
                  value={spaceId}
                  onChange={(event) => setSpaceId(event.target.value)}
                  required
                >
                  {spaces.map((space) => (
                    <option value={space.id} key={space.id}>
                      {space.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Тип
                <select
                  value={type}
                  onChange={(event) =>
                    setType(event.target.value as MaterialType)
                  }
                >
                  {materialTypes.map((item) => (
                    <option value={item.value} key={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Название
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Название источника"
                required
                autoFocus
              />
            </label>
            <label>
              Ссылка
              <input
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://…"
              />
            </label>
            <div className="form-row">
              <label>
                Автор
                <input
                  value={author}
                  onChange={(event) => setAuthor(event.target.value)}
                />
              </label>
              <label>
                Оценка времени, мин
                <input
                  min="0"
                  type="number"
                  value={minutes}
                  onChange={(event) => setMinutes(event.target.value)}
                />
              </label>
            </div>
            <label>
              Описание
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
          </>
        )}
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">
            Отмена
          </button>
          <button
            className="primary"
            disabled={saving || !spaceId}
            type="submit"
          >
            {saving ? "Сохраняем…" : "Добавить"}
          </button>
        </div>
      </form>
    </div>
  );
}
