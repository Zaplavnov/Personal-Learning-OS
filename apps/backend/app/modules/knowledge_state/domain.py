from enum import StrEnum


class KnowledgeDimension(StrEnum):
    RECALL = "recall"
    EXPLANATION = "explanation"
    STRUCTURE = "structure"
    COMPARISON = "comparison"
    APPLICATION = "application"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    STABILITY = "stability"


class EvidenceType(StrEnum):
    VIEWED = "viewed"
    NOTE_CREATED = "note_created"
    USER_EXPLANATION = "user_explanation"
    REVIEW_ANSWER = "review_answer"
    TASK_SOLVED = "task_solved"
    APPLIED_IN_PROJECT = "applied_in_project"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class ReviewType(StrEnum):
    RECALL = "recall"
    EXPLAIN = "explain"
    COMPARE = "compare"
    APPLY = "apply"
    STRUCTURE = "structure"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ReviewResult(StrEnum):
    FAILED = "failed"
    PARTIAL = "partial"
    PASSED = "passed"


REVIEW_DIMENSIONS: dict[ReviewType, KnowledgeDimension] = {
    ReviewType.RECALL: KnowledgeDimension.RECALL,
    ReviewType.EXPLAIN: KnowledgeDimension.EXPLANATION,
    ReviewType.COMPARE: KnowledgeDimension.COMPARISON,
    ReviewType.APPLY: KnowledgeDimension.APPLICATION,
    ReviewType.STRUCTURE: KnowledgeDimension.STRUCTURE,
}
