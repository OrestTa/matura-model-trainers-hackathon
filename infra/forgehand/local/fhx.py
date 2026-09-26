#!/usr/bin/env python3
"""fhx.py exec '<cmd>' | put <local> <remote> | get <remote> <local>  (session 01a0ddc1, cwd /scratch)"""
import base64, os, sys, re
sys.path.insert(0, "/home/user/matura-model-trainers-hackathon/infra/forgehand")
os.environ.setdefault("NODE_USE_ENV_PROXY", "1")
import fh_job
SESSION = os.environ.get("FHS", "01a0ddc1")
J = fh_job.Jupyter(SESSION)
def sh(cmd, t=None):
    out, code = J.sh("cd /scratch 2>/dev/null; " + cmd, timeout=int(t or os.environ.get("TIMEOUT", 600)))
    out = "\n".join(l for l in out.splitlines() if "bash_profile" not in l and "stty -echo" not in l and "__END_" not in l and not l.startswith("> "))
    return out, code
op = sys.argv[1]
if op == "exec":
    o, c = sh(sys.argv[2]); print(o); sys.exit(c or 0)
elif op == "put":
    data = base64.b64encode(open(sys.argv[2], "rb").read()).decode(); dst = sys.argv[3]
    sh(f"rm -f {dst}.b64")
    for i in range(0, len(data), 60000):
        o, c = sh(f"printf '%s' '{data[i:i+60000]}' >> {dst}.b64")
    o, c = sh(f"base64 -d {dst}.b64 > {dst} && rm {dst}.b64 && ls -la {dst}"); print(o)
elif op == "get":
    o, c = sh(f"base64 -w0 {sys.argv[2]}; echo")
    m = re.search(r"([A-Za-z0-9+/=]{8,})\s*$", o.strip())
    open(sys.argv[3], "wb").write(base64.b64decode(m.group(1))); print("got", sys.argv[3])
