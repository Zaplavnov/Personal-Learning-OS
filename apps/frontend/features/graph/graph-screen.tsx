"use client";

import { Link2, Network, Plus, Search, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import {
  ApiClientError,
  backendApi,
  type Concept,
  type ConceptRelation,
  type ConceptRelationType,
  type KnowledgeGraph,
  type LearningSpace,
} from "@/lib/api/client";

const relationTypes: { value: ConceptRelationType; label: string }[] = [
  { value: "prerequisite_of", label: "предшествует" },
  { value: "depends_on", label: "зависит от" },
  { value: "part_of", label: "часть" },
  { value: "example_of", label: "пример" },
  { value: "contrasts_with", label: "контрастирует" },
  { value: "often_confused_with", label: "часто путают" },
  { value: "used_in", label: "используется в" },
  { value: "derived_from", label: "выводится из" },
  { value: "analogous_to", label: "аналогично" },
  { value: "explains", label: "объясняет" },
];

function positionFor(index: number) {
  return { x: 8 + (index % 3) * 30, y: 12 + (Math.floor(index / 3) % 4) * 24 };
}

export function GraphScreen() {
  const [spaces, setSpaces] = useState<LearningSpace[]>([]);
  const [spaceId, setSpaceId] = useState("");
  const [graph, setGraph] = useState<KnowledgeGraph>({
    concepts: [],
    relations: [],
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingConcept, setCreatingConcept] = useState(false);
  const [creatingRelation, setCreatingRelation] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    backendApi
      .listLearningSpaces(controller.signal)
      .then((loadedSpaces) => {
        setSpaces(loadedSpaces);
        setSpaceId((current) => current || loadedSpaces[0]?.id || "");
        if (loadedSpaces.length === 0) setLoading(false);
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить пространства",
          );
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!spaceId) return;
    const controller = new AbortController();
    backendApi
      .getKnowledgeGraph(spaceId, controller.signal)
      .then((loadedGraph) => {
        setGraph(loadedGraph);
        setSelectedId((current) =>
          loadedGraph.concepts.some((concept) => concept.id === current)
            ? current
            : (loadedGraph.concepts[0]?.id ?? null),
        );
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof ApiClientError
              ? requestError.message
              : "Не удалось загрузить карту знаний",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [spaceId]);

  const visibleConcepts = useMemo(
    () =>
      graph.concepts.filter((concept) =>
        concept.title
          .toLocaleLowerCase("ru")
          .includes(query.toLocaleLowerCase("ru")),
      ),
    [graph.concepts, query],
  );
  const positions = useMemo(
    () =>
      new Map(
        graph.concepts.map((concept, index) => [
          concept.id,
          positionFor(index),
        ]),
      ),
    [graph.concepts],
  );
  const selected =
    graph.concepts.find((concept) => concept.id === selectedId) ?? null;
  const selectedRelations = graph.relations.filter(
    (relation) =>
      relation.source_concept_id === selectedId ||
      relation.target_concept_id === selectedId,
  );

  function addConcept(concept: Concept) {
    setGraph((current) => ({
      ...current,
      concepts: [...current.concepts, concept],
    }));
    setSelectedId(concept.id);
    setCreatingConcept(false);
  }

  function addRelation(relation: ConceptRelation) {
    setGraph((current) => ({
      ...current,
      relations: [...current.relations, relation],
    }));
    setCreatingRelation(false);
  }

  return (
    <>
      <PageHead
        eyebrow={
          loading
            ? "Загружаем карту"
            : `${graph.concepts.length} концепций · ${graph.relations.length} связей`
        }
        title="Карта знаний"
        action={
          <div className="head-actions">
            <button
              className="secondary"
              disabled={graph.concepts.length < 2}
              onClick={() => setCreatingRelation(true)}
              type="button"
            >
              <Link2 /> Связь
            </button>
            <button
              className="primary"
              disabled={!spaceId}
              onClick={() => setCreatingConcept(true)}
              type="button"
            >
              <Plus /> Концепция
            </button>
          </div>
        }
      />
      <div className="graph-toolbar">
        <select
          value={spaceId}
          onChange={(event) => setSpaceId(event.target.value)}
        >
          <option value="">Выбери пространство</option>
          {spaces.map((space) => (
            <option value={space.id} key={space.id}>
              {space.title}
            </option>
          ))}
        </select>
        <label>
          <Search />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Найти концепцию"
          />
        </label>
      </div>
      {error && <p className="inline-error">{error}</p>}
      {loading ? (
        <section className="card state-card">
          <span className="state-loader" />
          <h2>Строим карту…</h2>
        </section>
      ) : graph.concepts.length === 0 ? (
        <section className="card state-card">
          <span className="round-icon blue">
            <Network />
          </span>
          <h2>Карта начинается с первой концепции</h2>
          <p>
            Добавь центральную идею пространства, затем свяжи её с prerequisites
            и применениями.
          </p>
          <button
            className="primary"
            disabled={!spaceId}
            onClick={() => setCreatingConcept(true)}
            type="button"
          >
            <Plus /> Добавить концепцию
          </button>
        </section>
      ) : (
        <div className="graph-layout">
          <section className="knowledge-canvas card">
            <svg className="graph-edges" aria-hidden="true">
              {graph.relations.map((relation) => {
                const source = positions.get(relation.source_concept_id);
                const target = positions.get(relation.target_concept_id);
                return source && target ? (
                  <line
                    x1={`${source.x + 8}%`}
                    y1={`${source.y + 5}%`}
                    x2={`${target.x + 8}%`}
                    y2={`${target.y + 5}%`}
                    key={relation.id}
                  />
                ) : null;
              })}
            </svg>
            {visibleConcepts.map((concept) => {
              const position = positions.get(concept.id) ?? { x: 10, y: 10 };
              const relationCount = graph.relations.filter(
                (relation) =>
                  relation.source_concept_id === concept.id ||
                  relation.target_concept_id === concept.id,
              ).length;
              return (
                <button
                  style={{ left: `${position.x}%`, top: `${position.y}%` }}
                  key={concept.id}
                  onClick={() => setSelectedId(concept.id)}
                  className={`concept-node active ${selectedId === concept.id ? "selected" : ""}`}
                  type="button"
                >
                  <span>{concept.title}</span>
                  <small>{relationCount} связей</small>
                </button>
              );
            })}
          </section>
          <aside className="concept-panel card">
            {selected ? (
              <>
                <span className="status-pill">
                  {selected.status === "active" ? "Активна" : "Архив"}
                </span>
                <h2>{selected.title}</h2>
                <p>{selected.description ?? "Описание пока не добавлено."}</p>
                {selected.aliases.length > 0 && (
                  <p className="concept-aliases">
                    Также: {selected.aliases.join(", ")}
                  </p>
                )}
                <div className="mini-stats">
                  <div>
                    <strong>{selectedRelations.length}</strong>
                    <span>связей</span>
                  </div>
                  <div>
                    <strong>
                      {
                        selectedRelations.filter(
                          (item) => item.source_concept_id === selected.id,
                        ).length
                      }
                    </strong>
                    <span>исходящих</span>
                  </div>
                  <div>
                    <strong>
                      {
                        selectedRelations.filter(
                          (item) => item.target_concept_id === selected.id,
                        ).length
                      }
                    </strong>
                    <span>входящих</span>
                  </div>
                </div>
                <h4>Связи концепции</h4>
                <div className="relation-list">
                  {selectedRelations.length === 0 ? (
                    <p>Связей пока нет.</p>
                  ) : (
                    selectedRelations.map((relation) => {
                      const otherId =
                        relation.source_concept_id === selected.id
                          ? relation.target_concept_id
                          : relation.source_concept_id;
                      const other = graph.concepts.find(
                        (concept) => concept.id === otherId,
                      );
                      return (
                        <div key={relation.id}>
                          <span>
                            {relationTypes.find(
                              (item) => item.value === relation.relation_type,
                            )?.label ?? relation.relation_type}
                          </span>
                          <b>{other?.title}</b>
                        </div>
                      );
                    })
                  )}
                </div>
              </>
            ) : null}
          </aside>
        </div>
      )}
      {creatingConcept && (
        <ConceptModal
          spaceId={spaceId}
          onClose={() => setCreatingConcept(false)}
          onCreated={addConcept}
        />
      )}
      {creatingRelation && (
        <RelationModal
          concepts={graph.concepts}
          selectedId={selectedId}
          onClose={() => setCreatingRelation(false)}
          onCreated={addRelation}
        />
      )}
    </>
  );
}

function ConceptModal({
  spaceId,
  onClose,
  onCreated,
}: {
  spaceId: string;
  onClose: () => void;
  onCreated: (concept: Concept) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [aliases, setAliases] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      onCreated(
        await backendApi.createConcept({
          learning_space_id: spaceId,
          title,
          description: description || null,
          aliases: aliases
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось создать концепцию",
      );
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
        <p className="accent-label">Новая концепция</p>
        <h2>Добавь идею в карту</h2>
        <label>
          Название
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Описание
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Альтернативные названия
          <input
            value={aliases}
            onChange={(event) => setAliases(event.target.value)}
            placeholder="Через запятую"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary" type="submit">
            Добавить
          </button>
        </div>
      </form>
    </div>
  );
}

function RelationModal({
  concepts,
  selectedId,
  onClose,
  onCreated,
}: {
  concepts: Concept[];
  selectedId: string | null;
  onClose: () => void;
  onCreated: (relation: ConceptRelation) => void;
}) {
  const [sourceId, setSourceId] = useState(selectedId ?? concepts[0]?.id ?? "");
  const [targetId, setTargetId] = useState(
    concepts.find((concept) => concept.id !== sourceId)?.id ?? "",
  );
  const [relationType, setRelationType] =
    useState<ConceptRelationType>("prerequisite_of");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      onCreated(
        await backendApi.createConceptRelation({
          source_concept_id: sourceId,
          target_concept_id: targetId,
          relation_type: relationType,
          description: null,
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiClientError
          ? requestError.message
          : "Не удалось создать связь",
      );
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
        <p className="accent-label">Новая связь</p>
        <h2>Как связаны концепции?</h2>
        <label>
          Исходная концепция
          <select
            value={sourceId}
            onChange={(event) => {
              const next = event.target.value;
              setSourceId(next);
              if (targetId === next)
                setTargetId(
                  concepts.find((concept) => concept.id !== next)?.id ?? "",
                );
            }}
          >
            {concepts.map((concept) => (
              <option value={concept.id} key={concept.id}>
                {concept.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Тип связи
          <select
            value={relationType}
            onChange={(event) =>
              setRelationType(event.target.value as ConceptRelationType)
            }
          >
            {relationTypes.map((item) => (
              <option value={item.value} key={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Целевая концепция
          <select
            value={targetId}
            onChange={(event) => setTargetId(event.target.value)}
          >
            {concepts
              .filter((concept) => concept.id !== sourceId)
              .map((concept) => (
                <option value={concept.id} key={concept.id}>
                  {concept.title}
                </option>
              ))}
          </select>
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary" disabled={!targetId} type="submit">
            Связать
          </button>
        </div>
      </form>
    </div>
  );
}
