import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
import train_router

def test_features_ignore_answers_keys_and_labels():
    row={'question':'Wybierz odpowiedź','points':1,'images':[]}
    contaminated=dict(row,answer='secret',rubric='secret',category='essay',subtype='essay')
    assert train_router.features(row)==train_router.features(contaminated)

def test_fit_roundtrip_and_prediction():
    import json
    rows=[({'question':('wypracowanie argumentacja teza' if label=='essay' else label),'points':15 if label=='essay' else 1},label) for label in train_router.LABELS for _ in range(5)]
    model=json.loads(json.dumps(train_router.fit(rows)))
    assert train_router.predict({'question':'wypracowanie argumentacja teza','points':15},model)['subtype']=='essay'

def test_frozen_router_training_excludes_official_eval_papers():
    import json
    root=Path(__file__).resolve().parents[2]
    model=json.loads((root/'artifacts/small_track/router-real-source-disjoint.json').read_text())
    assert model['provenance']['exclusions']==[2023,2024]
    assert all('/2023-' not in s['path'] and '/2024-' not in s['path'] for s in model['provenance']['source_papers'])
