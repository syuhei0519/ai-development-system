"""Bounded direct product AC1/2 probe using retained exact-head OCI and fresh local DBs.
Existing procedures: ci/github/runtime.py and tests/orderintegration/order_test.go.
No rebuild, image/CI suite, preexisting DB, external publish or security exception.
Usage: python direct-ac-probe.py FIXED_CHECKOUT RETAINED_E3_ROOT NEW_PRIVATE_OUTPUT
"""
import datetime as dt, hashlib, ipaddress, json, os
from pathlib import Path
import secrets, subprocess, sys, time, urllib.error, urllib.request
checkout,images,root=map(lambda x:Path(x).resolve(),sys.argv[1:]);root.mkdir(mode=0o700,parents=True,exist_ok=True)
HEAD='24083aba485abd6b37bcbe71736fb543a847dcc6';BASE='2d3b2feff46ddd8d7091e6b4b5e95355c9bf34d0';PG='postgres@sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f'
def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,input=None):
 p=subprocess.run(args,input=input,capture_output=True,timeout=120)
 if p.returncode:raise RuntimeError('local fixture command refused: '+args[0])
 return p.stdout
assert run(['git','-C',str(checkout),'rev-parse','HEAD']).decode().strip()==HEAD
assert not run(['git','-C',str(checkout),'status','--porcelain']).strip()
result={'document_type':'direct_ac_measurements','producer':'order-b2-test-e4-a1','started_at':stamp(),'head_sha':HEAD,'base_sha':BASE,'target_revision':HEAD,'source_tree':run(['git','-C',str(checkout),'rev-parse','HEAD^{tree}']).decode().strip(),'valid_until':'2026-10-15T11:10:00Z','fixture_data':'Synthetic names/emails/items only in newly created disposable databases','http':[],'commands':[],'outcomes':{'AC-1':'unverified','AC-2':'unverified','AC-3':'unverified'},'image_rebuild':False,'image_ci_review_repeated':False,'no_existing_db_or_volume_used':True,'new_security_exceptions':False}
nonce=secrets.token_hex(12);prefix='order-b2-e4-'+nonce;network=prefix+'-net';containers=[];tags=[];net=False;private={'resource_names':{},'process_pids':{}}
env={k:v for k,v in os.environ.items() if not k.startswith('DOCKER_') and k not in ('GH_TOKEN','GITHUB_TOKEN')};env['DOCKER_CONFIG']=str(root/'private-docker')
def docker(*args,input=None):
 p=subprocess.run(['docker','--host','unix:///var/run/docker.sock',*args],input=input,capture_output=True,env=env,timeout=120)
 if p.returncode:raise RuntimeError('local Docker fixture step refused: '+args[0])
 return p.stdout
def inspect(name):return json.loads(docker('inspect',name))[0]
def sql(name,text):return docker('exec','-i',name,'psql','-U','postgres','-d',private['resource_names'][name]['database'],'-v','ON_ERROR_STOP=1','-At',input=text.encode()).decode().strip()
def request(svc,method,path,body=None,expected=200,ac=None):
 rawbody=None if body is None else (body.encode() if isinstance(body,str) else json.dumps(body).encode())
 req=urllib.request.Request(urls[svc]+path,data=rawbody,method=method,headers={'Content-Type':'application/json'})
 started=stamp()
 try:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=5) as resp:status=resp.status;raw=resp.read()
 except urllib.error.HTTPError as e:status=e.code;raw=e.read()
 entry={'started_at':started,'ended_at':stamp(),'service':svc,'method':method,'path':path,'expected_status':expected,'status':status,'response_sha256':sha(raw),'ac_ids':ac or []}
 if raw:
  try:entry['response']=json.loads(raw)
  except (ValueError,UnicodeError):entry['response_format']='non-JSON'
 result['http'].append(entry)
 assert status==expected,(svc,method,path,status,expected)
 return raw
urls={}
def wait_app(svc,name):
 address=inspect(name)['NetworkSettings']['Networks'][network]['IPAddress'];assert ipaddress.ip_address(address).is_private;urls[svc]='http://'+address+':8080'
 for _ in range(100):
  try:
   with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urls[svc]+'/readyz',timeout=1) as resp:
    if resp.status==200:return
  except (OSError,urllib.error.URLError):pass
  time.sleep(.1)
 raise RuntimeError('local app readiness timed out')
try:
 docker('image','inspect',PG)
 docker('network','create','--internal',network);net=True
 result['commands'].append('docker --host LOCAL_SOCKET network create --internal OWNED_NETWORK')
 services={}
 for svc,db,role in [('backend','accounts','account_app'),('order','orders','order_app')]:
  w=images/('chain-'+svc);layout=json.loads((w/'.security/public/layout.json').read_bytes());reader=json.loads((w/'.security/public/reader.json').read_bytes());archive=(w/'.oci/image.tar').read_bytes();assert sha(archive)==layout['archiveSha256'];assert layout['sourceCommit']==HEAD
  tag='docker.io/local/'+prefix+'-'+svc+':direct-ac';transport=root/(svc+'-runtime.tar')
  run([str(images/'bin/oci-runtime-export'),str(w/'.oci/layout'),layout['digest'],str(transport),tag])
  docker('load','--input',str(transport));tags.append(tag)
  image=json.loads(docker('image','inspect',tag))[0];assert image['Id']==reader['configDigest'];assert image['Config']['Labels']['org.opencontainers.image.revision']==HEAD
  dbname=prefix+'-'+svc+'-db';docker('create','--pull=never','--name',dbname,'--network',network,'--env','POSTGRES_PASSWORD='+nonce,PG);containers.append(dbname);private['resource_names'][dbname]={'database':db};docker('start',dbname)
  for _ in range(100):
   try:docker('exec',dbname,'pg_isready','-h','127.0.0.1','-U','postgres');break
   except RuntimeError:time.sleep(.1)
  else:raise RuntimeError('local DB readiness timed out')
  docker('exec','-i',dbname,'psql','-U','postgres','-v','ON_ERROR_STOP=1',input=(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD '{nonce}';\nCREATE DATABASE {db} OWNER {role};\n").encode())
  dsn=f'postgres://{role}:{nonce}@{dbname}:5432/{db}?sslmode=disable'
  flags=['--pull=never','--network',network,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','10001:10001','--env','DATABASE_URL='+dsn,'--env','LOG_LEVEL=error']
  migration=prefix+'-'+svc+'-migration';docker('create','--name',migration,*flags,tag,'migrate');containers.append(migration);docker('start',migration);assert docker('wait',migration).strip()==b'0'
  name=prefix+'-'+svc+'-api';docker('create','--name',name,*flags,tag);containers.append(name);docker('start',name);wait_app(svc,name)
  services[svc]={'db':dbname,'app':name,'history':'order_schema_migrations' if svc=='order' else 'schema_migrations','config_digest':reader['configDigest'],'image_digest':layout['digest'],'archive_sha256':layout['archiveSha256']}
  result['commands'].append('SERVICE: verify retained archive hash/source label/config ID; oci-runtime-export; docker load; fresh PostgreSQL create/start; create limited fixture role/database; existing SERVER migrate; SERVER start')
 result['runtime_binding']={svc:{k:v for k,v in x.items() if k.endswith('digest') or k=='archive_sha256'} for svc,x in services.items()}
 histories={svc:sql(x['db'],f"SELECT coalesce(json_agg(h ORDER BY version)::text,'[]') FROM {x['history']} h;") for svc,x in services.items()}
 account_raw=request('backend','POST','/api/accounts',{'name':'Synthetic AC Fixture','email':'ac-fixture@example.invalid'},201,['AC-2']);account=json.loads(account_raw);assert account['id']>0;account_path='/api/accounts/'+str(account['id'])
 assert json.loads(request('backend','GET',account_path,ac=['AC-2']))==account
 order_raw=request('order','POST','/api/orders',{'account_id':account['id'],'item_code':'AC-SYNTHETIC-001','quantity':2},201,['AC-1']);order=json.loads(order_raw);order_path='/api/orders/'+str(order['id']);assert order['account_id']==account['id'] and order['quantity']==2
 assert request('order','GET',order_path,ac=['AC-1'])==order_raw
 dbname=services['order']['db'];app=services['order']['app'];db_before=inspect(dbname);pid_before=inspect(app)['State']['Pid'];rows_before=sql(dbname,'SELECT json_agg(o ORDER BY id)::text FROM orders o;');start_restart=stamp()
 docker('restart','--time','10',app);wait_app('order',app);pid_after=inspect(app)['State']['Pid'];db_after=inspect(dbname);assert pid_before>0 and pid_after>0 and pid_before!=pid_after;assert db_before['Id']==db_after['Id'];assert db_before['Mounts']==db_after['Mounts'];assert db_before['State']['Pid']==db_after['State']['Pid']
 assert request('order','GET',order_path,ac=['AC-1'])==order_raw
 rows_after=sql(dbname,'SELECT json_agg(o ORDER BY id)::text FROM orders o;');assert rows_before==rows_after
 private['process_pids']={'before':pid_before,'after':pid_after,'database':db_before['State']['Pid']}
 result['restart']={'started_at':start_restart,'ended_at':stamp(),'command':'docker --host LOCAL_SOCKET restart --time 10 OWNED_ORDER_API','order_process_pid_changed':True,'database_container_unchanged':True,'database_process_unchanged':True,'database_volume_mounts_unchanged':True,'persisted_rows_before_after_equal':True,'row_snapshot_sha256_before':sha(rows_before.encode()),'row_snapshot_sha256_after':sha(rows_after.encode()),'created_and_retrieved_order_responses_byte_equal':True,'database_restarted':False}
 result['outcomes']['AC-1']='met';result['ac1_observed_at']=stamp()
 count_before=sql(dbname,'SELECT count(*) FROM orders;')
 request('order','POST','/api/orders',{'account_id':account['id'],'item_code':'AC-SYNTHETIC-001','quantity':0},400,['AC-2'])
 request('order','POST','/api/orders','{"account_id":',400,['AC-2'])
 request('backend','POST','/api/accounts',{'name':'','email':'invalid'},400,['AC-2'])
 assert sql(dbname,'SELECT count(*) FROM orders;')==count_before
 updated={'name':'Synthetic AC Updated','email':'ac-updated@example.invalid'}
 got=json.loads(request('backend','PUT',account_path,updated,200,['AC-2']));assert got['id']==account['id'] and got['name']==updated['name'] and got['email']==updated['email']
 got=json.loads(request('backend','GET',account_path,ac=['AC-2']));assert got['name']==updated['name'] and got['email']==updated['email']
 request('backend','DELETE',account_path,expected=204,ac=['AC-2']);request('backend','GET',account_path,expected=404,ac=['AC-2'])
 assert sql(services['backend']['db'],'SELECT count(*) FROM accounts;')=='0'
 assert histories=={svc:sql(x['db'],f"SELECT coalesce(json_agg(h ORDER BY version)::text,'[]') FROM {x['history']} h;") for svc,x in services.items()}
 result['migration_history_unchanged_after_initial_existing_migrations']=True;result['invalid_requests_zero_order_writes']=True;result['account_crud_verified']=True;result['outcomes']['AC-2']='met';result['ac2_observed_at']=stamp();result['status']='completed'
except Exception as e:
 result['status']='failed';result['error_type']=type(e).__name__;raise
finally:
 cleanup=[]
 for name in reversed(containers):
  try:docker('rm','--force','--volumes',name);cleanup.append(True)
  except Exception:cleanup.append(False)
 if net:
  try:docker('network','rm',network);cleanup.append(True)
  except Exception:cleanup.append(False)
 for tag in tags:
  try:docker('image','rm',tag);cleanup.append(True)
  except Exception:cleanup.append(False)
 for p in root.glob('*-runtime.tar'):p.unlink(missing_ok=True)
 result['cleanup']={'owned_containers_created':len(containers),'owned_images_loaded':len(tags),'all_owned_containers_anonymous_volumes_network_and_imported_tags_removed':bool(cleanup) and all(cleanup),'transport_tars_removed':not bool(list(root.glob('*-runtime.tar')))}
 result['ended_at']=stamp()
 if not all(cleanup):result['status']='blocked'
 (root/'measurement-original.json').write_text(json.dumps(result,indent=2)+'\n');(root/'runtime-identity-private.json').write_text(json.dumps(private,indent=2)+'\n')
print('PASS: direct product AC1/2 met; owned disposable resources removed')
