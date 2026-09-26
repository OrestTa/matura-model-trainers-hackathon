import importlib.util
import math
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('epoch_gate', ROOT / 'infra/small_track/train_bielik_epoch_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def scores(closed=2.0, opened=2.0):
    return [{'id': f'{route}-{i}', 'route': route, 'nll': value, 'target_tokens': 1 + i * 5}
            for route, count, value in zip(gate.ROUTES, (2, 10), (closed, opened)) for i in range(count)]


def test_gates_stop_regression_and_require_two_percent():
    assert not gate.decision(scores(), scores(2.1, 2.1))['continue_epoch2']
    assert not gate.decision(scores(), scores())['continue_epoch2']
    assert gate.decision(scores(), scores(1.8, 1.8))['continue_epoch2']
    assert not gate.decision(scores(), scores(1.8, 1.8), scores(1.79, 1.79))['select_epoch2']
    assert gate.decision(scores(), scores(1.8, 1.8), scores(1.7, 1.7))['select_epoch2']


def test_better_overall_cannot_hide_route_regression():
    result = gate.decision(scores(), scores(1.8, 1.8), scores(1.81, 1.5))
    assert result['epoch2']['overall'] < result['epoch1']['overall'] * .98
    assert not result['select_epoch2']


def test_mean_is_per_example_not_token_weighted():
    data = scores(1, 3)
    assert gate.summarize(data)['overall'] == pytest.approx(32 / 12)
    data[0]['target_tokens'] = 100000
    assert gate.summarize(data)['overall'] == pytest.approx(32 / 12)


@pytest.mark.parametrize('invalid', [scores()[:-1], scores() + scores()[:1], scores(float('nan'))])
def test_incomplete_nonfinite_refused(invalid):
    with pytest.raises(ValueError):
        gate.summarize(invalid)


class TinyTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {'tokenize': False, 'add_generation_prompt': True}
        assert [r['role'] for r in messages] == ['system', 'user']
        return 'PROMPT'
    def __call__(self, text, **kwargs):
        assert kwargs == {'add_special_tokens': False}
        return {'input_ids': [ord(c) for c in text]}


def tiny_row():
    return {'id': '2012-toy', 'year': 2012, 'synthetic': False, 'category': gate.ROUTES[0],
            'messages': [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'Q'},
                         {'role': 'assistant', 'content': 'A'}]}


def test_cpu_tiny_fixture_masks_prompt_and_includes_eos():
    row = tiny_row()
    encoded = gate.encode(TinyTokenizer(), row)
    assert encoded['labels'][:6] == [-100] * 6
    assert encoded['labels'][6:] == [ord(c) for c in 'A<|im_end|>']
    assert encoded['target_tokens'] == len('A<|im_end|>')
    # Causal loss consumes labels shifted one position; all answer/EOS labels survive.
    shifted = encoded['labels'][1:]
    assert sum(token != -100 for token in shifted) == encoded['target_tokens']
    # Tiny CPU likelihood fixture: prompt probability must not affect target mean.
    log_probs = [-100.] * 5 + [-math.log(2)] * encoded['target_tokens']
    masked_nll = -sum(lp for lp, label in zip(log_probs, shifted) if label != -100) / encoded['target_tokens']
    assert masked_nll == pytest.approx(math.log(2))


def test_long_row_fails_instead_of_truncating():
    row = tiny_row()
    row['messages'][-1]['content'] = 'A' * 3072
    with pytest.raises(ValueError, match='no truncation'):
        gate.encode(TinyTokenizer(), row)


@pytest.mark.parametrize('year', [2015, 2016, 2023, 2024, '2012'])
def test_reserved_or_noninteger_year_rejected(year):
    row = tiny_row()
    row['year'] = year
    with pytest.raises(ValueError):
        gate.check_row(row, gate.ROUTES[0], validation=True)


def test_frozen_local_data_preflight():
    data = ROOT / 'data/small_track_real_training_boundary_clean_v3'
    valid = ROOT / 'data/small_track_legacy_audit_20260927/optional-text-training.jsonl'
    if not data.exists() or not valid.exists():
        pytest.skip('Private local datasets deliberately not committed')
    train, validation = gate.load_frozen(data, valid)
    assert {k: len(v) for k, v in train.items()} == gate.COUNTS
    assert {k: len(v) for k, v in validation.items()} == gate.VAL_COUNTS


def test_changed_frozen_source_rejected(tmp_path):
    (tmp_path / 'manifest.json').write_text('{}')
    val = tmp_path / 'validation.jsonl'
    val.write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'):
        gate.load_frozen(tmp_path, val)
