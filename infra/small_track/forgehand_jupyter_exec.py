import argparse,base64,json,os,re,subprocess,time,uuid
from pathlib import Path
import requests,websocket
def main():
 p=argparse.ArgumentParser();p.add_argument('--command-file',required=True);p.add_argument('--upload');p.add_argument('--upload-path');a=p.parse_args()
 r=subprocess.run(['fh','session','jupyter','01a0ddc1-4922-7401-9766-86ab0f54739d'],env=dict(os.environ,XDG_CONFIG_HOME='/private/tmp/small-track-forgehand-config'),capture_output=True,text=True,timeout=20);u=re.findall(r'https://[^\s\x1b]+',r.stdout)[0]
 s=requests.Session();s.trust_env=False;rr=s.get(u,timeout=20);rr.raise_for_status();base=rr.url.split('/lab')[0].rstrip('/');xsrf=next((c.value for c in s.cookies if c.name=='_xsrf'),None)
 if xsrf:s.headers['X-XSRFToken']=xsrf
 if a.upload:
  path=a.upload_path;parts=path.split('/')
  for n in range(1,len(parts)):
   sub='/'.join(parts[:n]);check=s.get(base+'/api/contents/'+sub,timeout=15)
   if check.status_code==404:s.put(base+'/api/contents/'+sub,json={'type':'directory'},timeout=15).raise_for_status()
   else:check.raise_for_status()
  content=base64.b64encode(Path(a.upload).read_bytes()).decode();s.put(base+'/api/contents/'+path,json={'type':'file','format':'base64','content':content},timeout=30).raise_for_status();print('uploaded_bytes',Path(a.upload).stat().st_size,flush=True)
 terminal=s.post(base+'/api/terminals',json={},timeout=15);terminal.raise_for_status();name=terminal.json()['name'];print('own_terminal',name,flush=True);ws=None
 try:
  cookies='; '.join(c.name+'='+c.value for c in s.cookies);ws=websocket.create_connection(base.replace('https:','wss:')+'/terminals/websocket/'+name,cookie=cookies,origin=base,timeout=20)
  marker='CODEX_DONE_'+uuid.uuid4().hex;cmd=Path(a.command_file).read_text();encoded=base64.b64encode(cmd.encode()).decode();shell="printf '%s' '"+encoded+"' | base64 -d | bash; printf '\\n"+marker+":%s\\n' \"$?\"\n";ws.send(json.dumps(['stdin',shell]));end=time.time()+120;output=''
  while time.time()<end:
   try:msg=json.loads(ws.recv())
   except websocket.WebSocketTimeoutException:continue
   if msg[0]=='stdout':
    output+=msg[1]
    found=re.search(r'\r?\n'+marker+r':(\d+)',output)
    if found:
     # Shell echo contains our base64 command, never authentication material.
     lines=output.splitlines();print('\n'.join(l for l in lines if 'base64 -d | bash' not in l and marker not in l),flush=True);print('exit_code',found.group(1),flush=True);break
  else:raise TimeoutError('own terminal command timeout')
 finally:
  if ws:ws.close()
  s.delete(base+'/api/terminals/'+name,timeout=15).raise_for_status();print('own_terminal_deleted',name,flush=True)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  response=getattr(exc,'response',None)
  print('Jupyter operation failed:',type(exc).__name__,'HTTP',getattr(response,'status_code',None),'(credential-bearing details suppressed)',flush=True)
  raise SystemExit(1)
