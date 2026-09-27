#!/bin/bash
R=/scratch/claude-b15; P=/scratch/final_e2e/work/packages/probny-2026-01; B=/scratch/llama-build/bin; H=/scratch/h15
pkill -f "^bash /scratch/e4b.sh"; pkill -f "llama-server.*--port 809[3456]"; pkill -f "run_exam.py.*gemma4-e4b"; sleep 2
echo "$(date -u +%T) h15 start (E4B dropped)" >> $R/status.txt
rm -rf $H; mkdir -p $H; cp -r /scratch/b45h/. $H/
/scratch/.venv/bin/python - <<'PY'
import yaml;p='/scratch/h15/configs/models.yaml';d=yaml.safe_load(open(p))
b=dict(hf_id='second-state/Bielik-1.5B-v3.0-Instruct-GGUF',gguf_file='Bielik-1.5B-v3.0-Instruct-Q8_0.gguf',server='llamacpp',vision=False,params_b=1.6,disk_gb=1.70,gpu_gb=4)
d['models']['bielik-1.5b-q8']=dict(b,ocr=True);d['models']['bielik-1.5b-q8-noocr']=dict(b)
yaml.safe_dump(d,open(p,'w'),allow_unicode=True,sort_keys=False)
PY
sed -i "s#base_url: http://localhost:8093/v1#base_url: http://localhost:8091/v1#" $H/configs/routes.yaml
export LD_LIBRARY_PATH=$B
$B/llama-server -m /scratch/codex-bielik-cap-2135/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf --host 127.0.0.1 --port 8091 -ngl 999 -c 32768 --parallel 8 --jinja --cache-ram 0 > $R/server-h15.log 2>&1 &
until curl -sf localhost:8091/health >/dev/null; do sleep 1; done
arm() { # name key mode
  O=$R/$1; mkdir -p $O; s=$(date +%s)
  (cd $H && ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 /scratch/.venv/bin/python scripts/run_exam.py $P --model $2 --mode $3 --concurrency 3 -o $O/answers.json > $O/run.log 2>&1)
  echo "rc=$? wall $(( $(date +%s)-s ))s" >> $O/run.log
  python3 /scratch/smoke_e2e/scripts/check_submission.py $O/answers.json $P > $O/check.txt 2>&1
  echo "$(date -u +%T) $1: $(tail -2 $O/run.log | head -1 | cut -c1-60) | $(tail -1 $O/run.log) | $(tail -1 $O/check.txt)" >> $R/status.txt
}
arm h-routed-ocr bielik-1.5b-q8 routed &
arm h-routed-noocr bielik-1.5b-q8-noocr routed &
arm h-subtype-ocr bielik-1.5b-q8 subtype &
wait; echo "$(date -u +%T) H15 DONE" >> $R/status.txt
