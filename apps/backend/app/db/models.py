"""Import all models so Alembic can discover complete metadata."""

from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.jobs.models import Job
from app.modules.knowledge_state.infrastructure import (
    ConceptEvidence,
    ConceptState,
    ReviewAttempt,
    ReviewItem,
)
from app.modules.learning_paths.infrastructure import (
    LearningPath,
    LearningPathEdge,
    LearningPathNode,
    LearningPathNodeResource,
    LearningPathSuggestion,
    LearningPathVersion,
)
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace
from app.modules.materials.infrastructure import LearningSession, Material, Note
from app.modules.outbox.models import OutboxEvent
from app.modules.scheduler.infrastructure import CalendarItem, ScheduleVersion
from app.modules.users.models import User

__all__ = [
    "CalendarItem",
    "Concept",
    "ConceptEvidence",
    "ConceptRelation",
    "ConceptState",
    "Job",
    "LearningGoal",
    "LearningPath",
    "LearningPathEdge",
    "LearningPathNode",
    "LearningPathNodeResource",
    "LearningPathSuggestion",
    "LearningPathVersion",
    "LearningSession",
    "LearningSpace",
    "Material",
    "Note",
    "OutboxEvent",
    "ReviewAttempt",
    "ReviewItem",
    "ScheduleVersion",
    "User",
]
