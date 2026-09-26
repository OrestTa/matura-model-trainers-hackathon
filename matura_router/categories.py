"""Question categories the router knows about.

Each category maps to one LoRA adapter (see configs/routes.yaml). GENERAL is the
fallback: the untouched base model, used when the classifier is unsure.
"""

from enum import Enum


class Category(str, Enum):
    CLOSED_CHOICE = "closed_choice"      # pick A/B/C/D (one or more)
    TRUE_FALSE = "true_false"            # P/F per statement
    MATCHING = "matching"                # przyporządkuj / dobierz
    CHRONOLOGY = "chronology"            # uporządkuj chronologicznie
    SOURCE_ANALYSIS = "source_analysis"  # answer based on a quoted source, map, table
    SHORT_OPEN = "short_open"            # name / explain / give a date in a sentence or two
    ESSAY = "essay"                      # wypracowanie
    GENERAL = "general"                  # fallback to the base model

    @classmethod
    def specialised(cls) -> list["Category"]:
        return [c for c in cls if c is not cls.GENERAL]
