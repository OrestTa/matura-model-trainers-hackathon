"""Reference model sizes: the organisers' benchmark deck, not our own arithmetic.

Rule (Orest, 2026-09-26 15:47 CEST): model sizes come from Ania Olchowik's latest "Model
Benchmark" deck (Google Slides 1iGH2E6JURWe0Nq0Qqf0_nHoSA7s0LKaj5WSN6BpS3uI). Do not compute
them ourselves. Each entry in configs/models.yaml and configs/small_models.yaml carries

    deck_size_gb: {bf16: 23.92, 8bit: 11.96, 4bit: 5.98}   # copied from the deck, as printed
    ship_precision: 4bit                                   # the form we serve and ship

or `deck_size_gb: not in deck` when the deck doesn't list the model. The bf16 figures are on the
slide "Model memory without quantisation" (every model in the deck); 8-bit and 4-bit figures are
on the slide "Model memory after quantisation" (only the five 8B+ multimodal models). When the
deck has no figure for the precision we ship, the size is "not in deck" too.

Size checks (Orest, 15:55 CEST: "Always use the quantized size"): `reference_size()` uses the deck's
figure only when it is a QUANTIZED one (8bit/4bit) at the precision we ship; otherwise the published
size of the quantized file we ship (disk_gb, or the measured checkpoint). A bf16 deck figure is
information only and never fails a model.
"""

from __future__ import annotations

NOT_IN_DECK = "not in deck"


def deck_size(spec: dict) -> tuple[float | None, str]:
    """(size in GB from the deck for the precision we ship, or None; a label for the source)."""
    deck = spec.get("deck_size_gb")
    prec = str(spec.get("ship_precision", "bf16"))
    if isinstance(deck, dict) and deck.get(prec) is not None:
        return float(deck[prec]), f"deck {prec}"
    if isinstance(deck, dict):
        return None, f"{NOT_IN_DECK} at {prec}"
    return None, NOT_IN_DECK


def reference_size(spec: dict, fallback: float | None = None) -> tuple[float | None, str]:
    """Size for the limit checks: a quantized deck figure, else `fallback` (or disk_gb), the shipped file."""
    gb, label = deck_size(spec)
    if gb is not None and not label.endswith("bf16"):  # only a quantized deck figure counts
        return gb, label
    if gb is not None:
        label = "shipped file (deck has bf16 only)"
    fb = fallback if fallback is not None else spec.get("disk_gb")
    return (float(fb) if fb is not None else None), label
