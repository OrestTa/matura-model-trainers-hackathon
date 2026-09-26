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
