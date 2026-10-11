import subprocess,pathlib,hashlib,json,datetime
r=pathlib.Path(__file__).parent; repos=[pathlib.Path('/workspace/p0-test-'+p) for p in ['base','source']]; out={'document_type':'independent_render_schema_test','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'renders':[],'boundaries':[],'schema':[]}
for chart in ['root','platform','workloads']:
 for local in [False,True]:
  args=['helm','template',chart,'charts/'+chart]+(['-f','environments/local/'+chart+'.yaml'] if local else [])
  blobs=[subprocess.check_output(args,cwd=repo) for repo in repos]
  out['renders'].append(dict(chart=chart,local=local,equal=blobs[0]==blobs[1],sha256=[hashlib.sha256(b).hexdigest() for b in blobs],sizes=list(map(len,blobs))))
for path in ['bootstrap/namespaces.yaml','bootstrap/root-project.yaml','bootstrap/argocd-values.yaml','charts/root/templates/projects.yaml','charts/workloads/templates/applications.yaml']:
 blobs=[(repo/path).read_bytes() for repo in repos];out['boundaries'].append(dict(path=path,equal=blobs[0]==blobs[1],sha256=[hashlib.sha256(b).hexdigest() for b in blobs]))
O='a'*40
cases=[('default',[],0),('enabled',['--set','orderEnabled=true','--set-string','orderTargetRevision='+O],0),('disabled-staged',['--set-string','orderTargetRevision='+O],0)]
for val in ['', 'main','HEAD','v1.0','A'*40,'a'*39,'a'*41,'g'*40,' '+O,O+'\n']:
 cases.append(('revision-'+repr(val),['--set','orderEnabled=true','--set-string','orderTargetRevision='+val],1))
for key,values in [('orderEnabled',['null','1','{}','[]','"true"']),('orderTargetRevision',['null','1','true','{}','[]'])]:
 for val in values: cases.append((key+'='+val,['--set','orderEnabled=true','--set-json',key+'='+val],1))
for key,val in [('applicationRepository','https://example.invalid/a.git'),('targetRevision',O),('orderEnable','true')]: cases.append((key,['--set-string',key+'='+val],1))
for label,args,expected in cases:
 p=subprocess.run(['helm','template','workloads','charts/workloads']+args,cwd=repos[1],capture_output=True,text=True)
 out['schema'].append(dict(case=label,args=args,exit=p.returncode,expected=expected,matched=p.returncode==expected,stderr=p.stderr))
(r/'results'/'independent-render.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'renders_equal':sum(x['equal'] for x in out['renders']),'boundaries_equal':sum(x['equal'] for x in out['boundaries']),'schema_matched':sum(x['matched'] for x in out['schema']),'schema_total':len(cases)}))
