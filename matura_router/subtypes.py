"""Orest's five exam subtypes and a tuned setup (profile) for each.

    closed_text   closed task (choice, P/F, matching, order), no picture
    closed_image  closed task with a picture
    open_text     open task (source analysis, short answer), no picture
    open_image    open task with a picture
    essay         the essay

The subtype is known on stage without any key: the router's category (rule classifier) says
closed / open / essay, and the item's `images` list says whether a picture comes with it.
One base model serves every subtype; a profile only changes how it is asked (configs/subtypes.yaml):
prompt addition, thinking on or off, token budget, voting, OCR text next to the picture,
Wikipedia RAG, temperature and, once trained, a LoRA adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

import yaml

from .categories import Category

SUBTYPES = ("closed_text", "closed_image", "open_text", "open_image", "essay")
CLOSED = {Category.CLOSED_CHOICE, Category.TRUE_FALSE, Category.MATCHING, Category.CHRONOLOGY}
DEFAULT_SUBTYPES = Path(__file__).resolve().parent.parent / "configs" / "subtypes.yaml"


def subtype_of(category: Category | str, has_images: bool) -> str:
    category = Category(category)
    if category is Category.ESSAY:
        return "essay"
    kind = "closed" if category in CLOSED else "open"
    return f"{kind}_{'image' if has_images else 'text'}"


@dataclass
class Profile:
    """How one subtype is answered. None = keep the category route's own value."""
    name: str = "default"
    adapter: Optional[str] = None      # LoRA name (llama.cpp lora id map / vLLM model name); None = base
    max_tokens: Optional[int] = None   # answer budget; thinking adds think_tokens on top
    temperature: Optional[float] = None
    votes: Optional[int] = None        # majority vote over N answers (closed types only)
    vote_temperature: float = 0.7
    # Gemma 4 thinking (chat_template_kwargs.enable_thinking), on by default: Claude-graded over the
    # 4 held-out papers it gave 169/240 vs 126/240 without (docs/FINDINGS.md, 20:15 CEST).
    think: bool = True
    think_tokens: int = 8192           # reasoning budget on top of max_tokens (deck: 8,192; essay 16,384)
    rag: bool = False                  # Wikipedia BM25 passages before the task
    ocr: bool = False                  # vision model: add the pictures' OCR text next to the images
    prompt_suffix: str = ""            # appended to the category's system prompt
    extra: dict = field(default_factory=dict)  # merged into the request body

    @classmethod
    def from_dict(cls, name: str, d: dict | None) -> "Profile":
        d = dict(d or {})
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"subtype profile {name}: unknown keys {sorted(unknown)}")
        d.setdefault("name", name)
        return cls(**d)


def load_profiles(path: str | Path = DEFAULT_SUBTYPES) -> dict[str, Profile]:
    """{subtype: Profile} from configs/subtypes.yaml (`subtypes:` block); a missing subtype
    gets the plain routed setup."""
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    block = cfg.get("subtypes", cfg)
    return {st: Profile.from_dict(st, block.get(st)) for st in SUBTYPES}
