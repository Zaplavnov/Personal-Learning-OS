from enum import StrEnum


class MaterialType(StrEnum):
    VIDEO = "video"
    ARTICLE = "article"
    BOOK = "book"
    NOTEBOOK = "notebook"
    REPOSITORY = "repository"
    OTHER = "other"


class MaterialStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LearningSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class NoteType(StrEnum):
    INSIGHT = "insight"
    QUESTION = "question"
    GAP = "gap"
    EXAMPLE = "example"
    GENERAL = "general"
