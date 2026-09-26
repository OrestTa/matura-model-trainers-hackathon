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


def normalize_closed_answer(answer: str) -> str:
    """Compare explicit closed choices while retaining the original explanation.

    Conflicting repeated assignments are not collapsed. This parses syntax, not
    correctness, and must only be enabled for a candidate-classified closed task.
    """
    plain = unicodedata.normalize('NFKC', answer).casefold().strip()
    plain = re.sub(r'[*`_]', '', plain)
    pairs = re.findall(r'(?:^|[\n;,]|\s)([a-e]|\d+)\s*[:.)-]\s*(prawda|fałsz|p|f|[a-e]|\d+)\b', plain)
    if pairs:
        mapping = {}
        for key, value in pairs:
            value = {'prawda': 'p', 'fałsz': 'f'}.get(value, value)
            if key in mapping and mapping[key] != value:
                return normalize_answer(answer)
            mapping[key] = value
        return 'assignments:' + ';'.join(f'{key}={mapping[key]}' for key in sorted(mapping))
    choice = re.match(r'^(?:odpowiedź\s*:\s*)?([a-e])(?:[.)]|\s*[:–-])(?:\s|$)', plain)
    if choice:
        alternatives = re.findall(r'(?:^|\n)(?:odpowiedź\s*:\s*)?([a-e])[.)](?:\s|$)', plain)
        if all(option == choice[1] for option in alternatives):
            return choice[1]
    return normalize_answer(answer)


def choose_vote(samples: list[str], *, closed: bool = False) -> dict:
    """Require a strict majority of all scheduled samples; blanks cannot win.

    Without agreement, select the first nonblank sample. This is explicitly a
    fallback, not a semantic majority. Return original text without rewriting it.
    """
    if not samples or len(samples) % 2 != 1:
        raise ValueError('An odd, nonzero number of samples is required')
    if any(not isinstance(sample, str) for sample in samples):
        raise ValueError('Every sample must be a string; failures use empty strings')
    normalizer = normalize_closed_answer if closed else normalize_answer
    normalized = [normalizer(sample) for sample in samples]
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
        'selector': 'offline-closed-structured-majority-v2' if closed else 'offline-lexical-majority-v1',
    }
