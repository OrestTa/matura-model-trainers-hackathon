import copy
import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/small_track'))
import harness

class HarnessTests(unittest.TestCase):
    def config(self):
        return {'artifacts':{'base':{'sha256':'a'*64,'bytes':100,'role':'weights'},'vision':{'sha256':'b'*64,'bytes':30,'role':'vision'},'adapter':{'sha256':'c'*64,'bytes':4,'role':'adapter'}},'routes':{label:{'model':'base','base_url':'http://localhost:8000/v1','own_model_endpoint':True,'artifacts':['base','vision','adapter']} for label in harness.LABELS}}

    def test_shared_weights_counted_once_and_vision_included(self):
        summary=harness.validate_config(self.config())
        self.assertEqual(summary['sum_unique_artifact_bytes'],134)
        self.assertEqual(summary['max_individual_model_bytes'],130)

    def test_distinct_models_counted(self):
        config=self.config();config['artifacts']['other']={'sha256':'d'*64,'bytes':50,'role':'weights'}
        config['routes']['essay'].update(model='other',artifacts=['other'])
        self.assertEqual(harness.validate_config(config)['sum_unique_weights_and_vision_bytes'],180)

    def test_no_hidden_adapter_omission(self):
        config=self.config();config['routes']['essay']['adapter']='lora'
        with self.assertRaises(ValueError):harness.validate_config(config)

    def test_unmeasured_not_zero(self):
        config=self.config();config['routes']['essay']['artifacts']=[]
        self.assertIsNone(harness.validate_config(config)['max_individual_model_bytes'])

    def test_grading_input_rejected(self):
        with self.assertRaises(ValueError):harness.infer.messages({'question':'Q','official_solution':'secret'})

    def test_route_and_adapter_alias(self):
        config=self.config();config['routes']['essay'].update(adapter='essay_lora',adapter_model='essay_alias')
        row={'id':'p-z1','task_id':'1','subtype':'essay','question':'Q'}
        with patch.object(harness.infer,'answer',return_value={}) as answer:
            output=harness.run_row(row,config,'hash','.')
        self.assertEqual(answer.call_args.args[1].model,'essay_alias')
        self.assertEqual(output['task_id'],'1')


    def test_all_blank_vote_preserves_failure(self):
        config=self.config();config['vote_samples']=3
        row={'id':'a','question':'Q','subtype':'essay','points':15}
        with patch('harness.infer.answer',return_value={'answer':'','error':'empty_answer'}):
            out=harness.run_row(row,config,'hash','.')
        self.assertEqual(out['error'],'empty_answer')
        self.assertIsNone(out['vote']['chosen_index'])

    def test_router_and_ocr_bytes_counted(self):
        config=self.config();config['auxiliary_artifacts']=[{'sha256':'e'*64,'bytes':7,'role':'router'},{'sha256':'f'*64,'bytes':11,'role':'ocr'}]
        self.assertEqual(harness.validate_config(config)['sum_unique_artifact_bytes'],152)
