"""Predeclared two-route epoch ablation. Default: CPU-only data validation.

No exam evaluation inputs. Execute only in the isolated native runtime, with an
outer timeout. Validation targets are never used for gradients or routing.
"""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

ROUTES = ('closed_without_images', 'open_without_images')
TRAIN_SHA = 'da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab'
VALID_SHA = '39787692d5d6b8990d6f8f6a5bfa8b94dc0fc7bf377cc649f1eef6ad69db2122'
MODEL_SHA = '3c337d1d0d3f8cafb27f617b97a9a0cf70a2067648cb3946311e2fe370c28978'
MODEL_REV = 'a3a660b10fdba3a7b03c3349567e54d8875f9ac9'
COUNTS = dict(zip(ROUTES, (25, 76)))
VAL_COUNTS = dict(zip(ROUTES, (2, 10)))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def check_row(row, route, validation=False):
    if row.get('synthetic') is not False or row.get('category') != route:
        raise ValueError('Only real, correctly categorized text rows are permitted')
    year = row.get('year')
    if not isinstance(year, int) or year in (2015, 2016, 2023, 2024):
        raise ValueError('Reserved/evaluation source year forbidden')
    if validation and year not in (2012, 2014):
        raise ValueError('Validation source must be 2012 or 2014')
    messages = row.get('messages', [])
    if [m.get('role') for m in messages] != ['system', 'user', 'assistant']:
        raise ValueError('Expected system, user, assistant messages')
    if any(not isinstance(m.get('content'), str) or not m['content'].strip() for m in messages):
        raise ValueError('Empty or nontext message')


def load_frozen(data, validation):
    data = Path(data)
    if sha(data / 'manifest.json') != TRAIN_SHA or sha(validation) != VALID_SHA:
        raise ValueError('Frozen data hash mismatch')
    manifest = json.loads((data / 'manifest.json').read_text())
    train, valid = {}, {}
    val_rows = rows(validation)
    if len(val_rows) != 12:
        raise ValueError('Expected exactly 12 validation examples')
    ids = set()
    for route in ROUTES:
        path = data / route / 'train.jsonl'
        if sha(path) != manifest['files'][route]['sha256']:
            raise ValueError('Training route file hash mismatch')
        train[route] = rows(path)
        valid[route] = [r for r in val_rows if r.get('category') == route]
        if len(train[route]) != COUNTS[route] or len(valid[route]) != VAL_COUNTS[route]:
            raise ValueError('Frozen route counts mismatch')
        for split, collection in (('train', train[route]), ('validation', valid[route])):
            for row in collection:
                check_row(row, route, split == 'validation')
                if row['id'] in ids:
                    raise ValueError('Duplicate ID or training/validation overlap')
                ids.add(row['id'])
    return train, valid


def encode(tokenizer, row):
    prompt = tokenizer.apply_chat_template(row['messages'][:-1], tokenize=False, add_generation_prompt=True)
    before = tokenizer(prompt, add_special_tokens=False)['input_ids']
    target = tokenizer(row['messages'][-1]['content'] + '<|im_end|>', add_special_tokens=False)['input_ids']
    if not before or not target or len(before) + len(target) > 3072:
        raise ValueError(f"{row['id']}: empty tokens or exceeds 3072; no truncation/exclusion allowed")
    return {'id': row['id'], 'input_ids': before + target,
            'labels': [-100] * len(before) + target, 'target_tokens': len(target)}


def summarize(items):
    if len(items) != 12 or len({r['id'] for r in items}) != 12:
        raise ValueError('Incomplete or duplicate validation predictions')
    means = {}
    for route in ROUTES:
        subset = [r for r in items if r['route'] == route]
        if len(subset) != VAL_COUNTS[route]:
            raise ValueError('Invalid validation route count')
        if any(not math.isfinite(r['nll']) or r['nll'] < 0 for r in subset):
            raise ValueError('Invalid validation NLL')
        means[route] = sum(r['nll'] for r in subset) / len(subset)
    return {'overall': sum(r['nll'] for r in items) / len(items), 'routes': means,
            'aggregation': 'unweighted mean of per-example assistant-token mean NLL'}


def decision(base, epoch1, epoch2=None):
    base_s, first_s = summarize(base), summarize(epoch1)
    if {r['id'] for r in base} != {r['id'] for r in epoch1}:
        raise ValueError('Validation IDs differ')
    result = {'base': base_s, 'epoch1': first_s,
              'continue_epoch2': first_s['overall'] < base_s['overall'],
              'select_epoch2': False}
    if epoch2 is not None:
        if {r['id'] for r in epoch1} != {r['id'] for r in epoch2}:
            raise ValueError('Validation IDs differ')
        second_s = summarize(epoch2)
        result['epoch2'] = second_s
        result['select_epoch2'] = (result['continue_epoch2'] and
            second_s['overall'] <= first_s['overall'] * 0.98 and
            all(second_s['routes'][route] <= first_s['routes'][route] for route in ROUTES))
        before = {r['id']: r['nll'] for r in epoch1}
        result['per_example_epoch2_minus_epoch1'] = {r['id']: r['nll'] - before[r['id']] for r in epoch2}
    return result


def write(path, content):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def execute(args, train, valid):
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model, PeftModel
    from train_bielik_real_native import memory_preflight

    started = time.monotonic()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    def deadline():
        if time.monotonic() - started >= 870:
            raise TimeoutError('Internal 870-second work deadline; outer timeout still required')
    def free_gate():
        deadline()
        mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        if int(mem['MemAvailable'].split()[0]) * 1024 < 6 * (1 << 30):
            raise RuntimeError('Host MemAvailable below six GiB')
        return memory_preflight(torch, 0.20)
    model_path = Path(args.model)
    if sha(model_path / 'model.safetensors') != MODEL_SHA:
        raise ValueError('Native weight SHA mismatch')
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    encoded = {split: {route: [encode(tokenizer, row) for row in payload[route]] for route in ROUTES}
               for split, payload in (('train', train), ('validation', valid))}
    write(output / 'protocol.json', {'train_manifest_sha256': TRAIN_SHA, 'validation_sha256': VALID_SHA,
          'native_revision': MODEL_REV, 'native_weight_sha256': MODEL_SHA,
          'counts': COUNTS, 'validation_counts': VAL_COUNTS, 'epochs_max': 2,
          'learning_rate': 5e-5, 'rank': 8, 'alpha': 16, 'dropout': 0,
          'seeds': [7291, 7292], 'token_limit': 3072, 'excluded': [],
          'validation_token_counts': {route: {r['id']: r['target_tokens'] for r in encoded['validation'][route]} for route in ROUTES},
          'validation_used_for_gradients': False})
    def load_base():
        gate = free_gate()
        torch.manual_seed(7291)
        torch.cuda.manual_seed_all(7291)
        model = AutoModelForCausalLM.from_pretrained(model_path, dtype=torch.bfloat16,
            device_map={'': 'cuda'}, local_files_only=True)
        return model, gate
    def tensor(row):
        return {name: torch.tensor([row[name]], device='cuda') for name in ('input_ids', 'labels')}
    def evaluate(model, route):
        model.eval()
        result = []
        with torch.inference_mode():
            for row in encoded['validation'][route]:
                deadline()
                batch = tensor(row)
                loss = model(**batch, attention_mask=torch.ones_like(batch['input_ids'])).loss
                value = float(loss.float().item())
                if not math.isfinite(value):
                    raise ValueError('Nonfinite validation loss')
                result.append({'id': row['id'], 'route': route, 'nll': value,
                               'target_tokens': row['target_tokens']})
        return result
    def one_epoch(model, opt, route, epoch):
        model.train()
        model.enable_input_require_grads()
        model.gradient_checkpointing_enable()
        order = list(encoded['train'][route])
        random.Random(7290 + epoch).shuffle(order)
        report = []
        for row in order:
            deadline()
            batch = tensor(row)
            opt.zero_grad(set_to_none=True)
            loss = model(**batch, attention_mask=torch.ones_like(batch['input_ids'])).loss
            if not bool(torch.isfinite(loss)):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1)
            opt.step()
            item = {'id': row['id'], 'loss': float(loss.detach()), 'route': route, 'epoch': epoch}
            report.append(item)
            print(json.dumps(item), flush=True)
        checkpoint = output / route / f'epoch{epoch}'
        checkpoint.mkdir(parents=True)
        model.save_pretrained(checkpoint / 'adapter')
        torch.save({'optimizer': opt.state_dict(), 'cpu_rng': torch.get_rng_state(),
                    'cuda_rng': torch.cuda.get_rng_state_all(), 'epoch': epoch,
                    'train_manifest_sha256': TRAIN_SHA, 'validation_sha256': VALID_SHA,
                    'used_ids': [r['id'] for r in report],
                    'trainable_parameter_names': [n for n, p in model.named_parameters() if p.requires_grad]}, checkpoint / 'optimizer.pt')
        write(checkpoint / 'training.json', report)
        return checkpoint
    def optimizer(model):
        return torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=5e-5)
    base_scores, first_scores, second_scores = [], [], []
    for route in ROUTES:
        model, gate = load_base()
        base_scores.extend(evaluate(model, route))
        targets = [name for name, module in model.named_modules()
                   if name.endswith(('.mlp.gate_proj', '.mlp.up_proj', '.mlp.down_proj'))]
        if not targets:
            raise ValueError('No MLP modules')
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=targets,
                         lora_dropout=0.0, task_type='CAUSAL_LM'))
        opt = optimizer(model)
        checkpoint = one_epoch(model, opt, route, 1)
        first_scores.extend(evaluate(model, route))
        write(checkpoint / 'resource-gate.json', gate)
        del opt, model
        torch.cuda.empty_cache()
        write(output / 'base-nll.json', base_scores)
        write(output / 'epoch1-nll.json', first_scores)
    result = decision(base_scores, first_scores)
    write(output / 'decision.json', result)
    if not result['continue_epoch2']:
        return result
    for route in ROUTES:
        model, gate = load_base()
        previous = output / route / 'epoch1'
        model = PeftModel.from_pretrained(model, previous / 'adapter', is_trainable=True, local_files_only=True)
        opt = optimizer(model)
        # Only load the trusted checkpoint written above in this fresh, unique run.
        saved = torch.load(previous / 'optimizer.pt', map_location='cpu', weights_only=True)
        if saved['train_manifest_sha256'] != TRAIN_SHA or saved['validation_sha256'] != VALID_SHA or saved['epoch'] != 1:
            raise ValueError('Checkpoint provenance mismatch')
        if saved['trainable_parameter_names'] != [n for n, p in model.named_parameters() if p.requires_grad]:
            raise ValueError('Optimizer parameter ordering differs from saved checkpoint')
        opt.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['cpu_rng'])
        torch.cuda.set_rng_state_all(saved['cuda_rng'])
        checkpoint = one_epoch(model, opt, route, 2)
        second_scores.extend(evaluate(model, route))
        write(checkpoint / 'resource-gate.json', gate)
        del opt, model
        torch.cuda.empty_cache()
        write(output / 'epoch2-nll.json', second_scores)
    result = decision(base_scores, first_scores, second_scores)
    write(output / 'decision.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True)
    p.add_argument('--validation', required=True)
    p.add_argument('--model')
    p.add_argument('--output')
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    train, valid = load_frozen(args.data, args.validation)
    if not args.execute:
        print(json.dumps({'status': 'CPU data preflight passed; no model loaded', 'training_rows': 101,
                          'validation_rows': 12, 'train_manifest_sha256': TRAIN_SHA, 'validation_sha256': VALID_SHA}))
        return
    if not args.model or not args.output:
        p.error('--execute requires --model and new --output')
    print(json.dumps(execute(args, train, valid)), flush=True)


if __name__ == '__main__':
    main()
