"""Independent attempt3 runner; upstream scripts retained byte-for-byte.
Run: python run_reproducers.py HEAD BASELINE OLD OUTPUT_DIR
Synthetic cases only. No changes to implementation, no external operations.
"""
import datetime, json, pathlib, subprocess, sys
head, baseline, old, output = map(lambda s: pathlib.Path(s).resolve(), sys.argv[1:])
scripts = pathlib.Path(__file__).resolve().parent/'reproducers'
rows=[]
tasks=[
 ('independent-head','independent_cases.py',head,[str(baseline)]),
 ('samples-head','sample_checks.py',head,[]),
 ('aggregate-original-old','aggregate_reproducer.py',old,[]),
 ('fifo-original-old','fifo_reproducer.py',old,[]),
 ('aggregate-original-head','aggregate_reproducer.py',head,[]),
 ('fifo-original-head','fifo_reproducer.py',head,[]),
 ('aggregate-v2-head','aggregate_reproducer_v2.py',head,[]),
 ('fifo-v2-head','fifo_reproducer_v2.py',head,[]),
]
for name, script, checkout, args in tasks:
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 cmd=[sys.executable,str(scripts/script),str(checkout),*args,str(output/(name+'.json'))]
 result=subprocess.run(cmd,capture_output=True,text=True,timeout=240,cwd=checkout)
 text=result.stdout+result.stderr
 for path, alias in [(scripts,'<REPRODUCERS>'),(head,'<HEAD>'),(baseline,'<BASELINE>'),(old,'<OLD>'),(output,'<OUTPUT>')]:
  text=text.replace(str(path),str(alias))
 (output/(name+'.txt')).write_text(text)
 rows.append(dict(case=name,script=script,checkout_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip(),started_at=start,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,output_file=name+'.txt',result_file=name+'.json' if (output/(name+'.json')).exists() else None))
 (output/'reproducer-runs.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(name, result.returncode, flush=True)
