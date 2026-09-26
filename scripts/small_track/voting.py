"""Offline answer consensus: select an existing sample, never consult a key or API."""
from __future__ import annotations

from collections import Counter
import re
import unicodedata


def normalize_answer(answer: str) -> str:
    """Conservative lexical equivalence; no semantic grading or invented answers."""
    text = unicodedata.normalize('NFKC', answer).strip().casefold()
    text = re.sub(r'\s+', ' ', text)
    # Normalize only a complete single option, not prose or multi-part answers.
    if re.fullmatch(r'[a-e][.)]?', text):
        return text[0]
    if text in {'tak', 'tak.', 'yes', 'yes.'}:
        return 'tak'
    if text in {'nie', 'nie.', 'no', 'no.'}:
        return 'nie'
    return text


def choose_vote(samples: list[str]) -> dict:
    """Require a strict majority of all scheduled samples; blanks cannot win.

    Without agreement, select the first nonblank sample. This is explicitly a
    fallback, not a semantic majority. Return original text without rewriting it.
    """
    if not samples or len(samples) % 2 != 1:
        raise ValueError('An odd, nonzero number of samples is required')
    if any(not isinstance(sample, str) for sample in samples):
        raise ValueError('Every sample must be a string; failures use empty strings')
    normalized = [normalize_answer(sample) for sample in samples]
    counts = Counter(value for value in normalized if value)
    threshold = len(samples) // 2 + 1
    winner = next((value for value in normalized if value and counts[value] >= threshold), None)
    has_majority = winner is not None
    if winner is None:
        winner = next((value for value in normalized if value), None)
    index = normalized.index(winner) if winner is not None else None
    return {
        'answer': samples[index] if index is not None else '',
        'chosen_index': index,
        'agreement_count': counts[winner] if winner is not None else 0,
        'sample_count': len(samples),
        'majority_threshold': threshold,
        'has_majority': has_majority,
        'selection_reason': 'lexical_majority' if has_majority else (
            'first_nonblank_fallback' if index is not None else 'all_samples_empty'),
        'normalized_votes': normalized,
        'selector': 'offline-lexical-majority-v1',
    }
