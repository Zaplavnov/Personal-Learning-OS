from enum import StrEnum


class LearningSpaceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class LearningGoalStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
