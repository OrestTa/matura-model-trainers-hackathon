import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('voting', Path(__file__).resolve().parents[2] / 'scripts/small_track/voting.py')
voting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voting)


def test_two_of_three_selects_original_option():
    result = voting.choose_vote(['B', 'A.', 'a'])
    assert result['answer'] == 'A.'
    assert result['chosen_index'] == 1
    assert result['has_majority'] and result['agreement_count'] == 2


def test_open_answers_without_consensus_are_labeled_fallback():
    result = voting.choose_vote(['Pierwsza odpowiedź.', 'Druga odpowiedź.', 'Trzecia odpowiedź.'])
    assert result['answer'] == 'Pierwsza odpowiedź.'
    assert not result['has_majority']
    assert result['selection_reason'] == 'first_nonblank_fallback'


def test_failures_do_not_reduce_majority_threshold():
    result = voting.choose_vote(['', '', 'A'])
    assert result['answer'] == 'A'
    assert not result['has_majority'] and result['majority_threshold'] == 2
    assert voting.choose_vote(['', ' ', ''])['chosen_index'] is None


def test_prose_is_not_reduced_to_single_option():
    result = voting.choose_vote(['A', 'A ponieważ pierwszy opis pasuje.', 'B'])
    assert not result['has_majority']


def test_polish_yes_no_and_whitespace():
    assert voting.choose_vote(['Nie.', 'tak', 'NO'])['answer'] == 'Nie.'
    assert voting.choose_vote(['Dwa  zdania', 'dwa\nzdania', 'inne'])['has_majority']


def test_invalid_batch_rejected():
    for batch in ([], ['A', 'A'], ['A', None, 'A']):
        with pytest.raises(ValueError):
            voting.choose_vote(batch)


def test_closed_mapping_ignores_explanation_but_preserves_original():
    samples = ['A: 1\nB: 3\nA: 1\nB: 2', 'A: 1 (wyjaśnienie)\nB: 2', 'A: 1\nB: 2']
    result = voting.choose_vote(samples, closed=True)
    assert result['chosen_index'] == 1
    assert result['answer'] == samples[1]
    assert result['agreement_count'] == 2
    assert not voting.choose_vote(samples)['has_majority']


def test_closed_true_false_vectors_and_single_choice():
    assert voting.choose_vote(['1. P\n2. F', '1: prawda; 2: fałsz', '1. F\n2. P'], closed=True)['has_majority']
    assert voting.choose_vote(['B', 'A. Wyjaśnienie', '**A.** Inne wyjaśnienie'], closed=True)['chosen_index'] == 1


def test_conflicting_or_partial_mappings_do_not_merge():
    result = voting.choose_vote(['A: 1\nA: 2', 'A: 2\nB: 1', 'A: 2'], closed=True)
    assert not result['has_majority']
