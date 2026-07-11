from enum import StrEnum


class ConceptStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConceptRelationType(StrEnum):
    PREREQUISITE_OF = "prerequisite_of"
    DEPENDS_ON = "depends_on"
    PART_OF = "part_of"
    EXAMPLE_OF = "example_of"
    GENERALIZATION_OF = "generalization_of"
    SPECIAL_CASE_OF = "special_case_of"
    CONTRASTS_WITH = "contrasts_with"
    OFTEN_CONFUSED_WITH = "often_confused_with"
    USED_IN = "used_in"
    DERIVED_FROM = "derived_from"
    ANALOGOUS_TO = "analogous_to"
    EXPLAINS = "explains"
    IMPLEMENTED_BY = "implemented_by"
