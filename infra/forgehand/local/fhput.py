import base64, json, os, sys, time, uuid, textwrap
sys.path.insert(0, "/home/user/matura-model-trainers-hackathon/infra/forgehand")
import fh_job, websocket
from urllib.parse import urlparse
J = fh_job.Jupyter(os.environ.get("FHS", "01a0ddc1"))
src, dst = sys.argv[1], sys.argv[2]
data = base64.b64encode(open(src, "rb").read()).decode()
name = J.api("POST", "/api/terminals")["name"]
ws_url = J.base.replace("https://", "wss://")
headers = [f"{k}: {v}" for k, v in J.http.headers.items() if k == "Authorization"]
cookie = "; ".join(f"{c.name}={c.value}" for c in J.http.cookies)
p = urlparse(os.environ.get("HTTPS_PROXY", ""))
ws = websocket.create_connection(f"{ws_url}/terminals/websocket/{name}", header=headers, cookie=cookie or None,
    http_proxy_host=p.hostname, http_proxy_port=p.port, proxy_type="http", sslopt={"ca_certs": fh_job.CA}, timeout=600)
ws.send(json.dumps(["stdin", f"stty -echo; cat > {dst}.b64\n"])); time.sleep(1)
lines = textwrap.wrap(data, 2000)
for i in range(0, len(lines), 50):
    ws.send(json.dumps(["stdin", "\n".join(lines[i:i+50]) + "\n"]))
ws.send(json.dumps(["stdin", "\x04"])); time.sleep(1)
mark = uuid.uuid4().hex[:8]
ws.send(json.dumps(["stdin", f"base64 -d {dst}.b64 > {dst} && rm {dst}.b64; md5sum {dst}; echo DONE_{mark}\n"]))
out, dl = "", time.time() + 300
while time.time() < dl and f"DONE_{mark}" not in out.split("echo DONE")[-1]:
    m = json.loads(ws.recv())
    if m[0] == "stdout": out += m[1]
print(out[-300:]); ws.close(); J.api("DELETE", f"/api/terminals/{name}")
