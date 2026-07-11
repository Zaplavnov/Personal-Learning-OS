"""Import all models so Alembic can discover complete metadata."""

from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.jobs.models import Job
from app.modules.knowledge_state.infrastructure import (
    ConceptEvidence,
    ConceptState,
    ReviewAttempt,
    ReviewItem,
)
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace
from app.modules.materials.infrastructure import LearningSession, Material, Note
from app.modules.outbox.models import OutboxEvent
from app.modules.users.models import User

__all__ = [
    "Concept",
    "ConceptEvidence",
    "ConceptRelation",
    "ConceptState",
    "Job",
    "LearningGoal",
    "LearningSession",
    "LearningSpace",
    "Material",
    "Note",
    "OutboxEvent",
    "ReviewAttempt",
    "ReviewItem",
    "User",
]
