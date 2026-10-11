"""Independent attempt 3 synthetic probes; immutable product checkout selected by PB_HEAD."""
import os,sys,json,copy,re,unittest,importlib.util
from pathlib import Path
root=Path(os.environ['PB_HEAD']);sys.path.insert(0,str(root))
from scripts import knowledge_collector as c
class Attempt3(unittest.TestCase):
 def event(self):return json.loads(next((root/'examples/knowledge-collector/events').glob('*.json')).read_bytes())
 def test_identity_all_six_dimensions_sensitive_size_ignored(self):
  e=self.event();old=c.event_id(e)
  for field,value in [('repository','synthetic/other'),('commit','f'*40),('path','other.md'),('sha256','e'*64)]:
   n=copy.deepcopy(e);n['source_ref'][field]=value;self.assertNotEqual(c.event_id(n),old,field)
  for field,value in [('candidate_id','SYNTHETIC-DIFFERENT'),('event_kind','invalidation')]:
   n=copy.deepcopy(e);n[field]=value;self.assertNotEqual(c.event_id(n),old,field)
  e['source_ref']['size']+=1;self.assertEqual(c.event_id(e),old)
 def test_correction_and_invalidation_have_distinct_valid_identity(self):
  e=self.event();old=e['event_id'];ids={old}
  for kind in ['correction','invalidation']:
   n=copy.deepcopy(e);n['event_kind']=kind;n['supersedes']=[old];n['event_id']=c.event_id(n);c.validate_event(n);ids.add(n['event_id'])
  self.assertEqual(len(ids),3)
  n['event_kind']='correction';n['supersedes']=[];n['event_id']=c.event_id(n)
  with self.assertRaises(ValueError):c.validate_event(n)
 def test_current_docs_local_links_and_scope(self):
  docs=[root/'README.md']+[f for d in ['contracts','workflows','templates'] for f in (root/d).glob('*.md')]
  for f in docs:
   text=f.read_text();self.assertNotIn('後続P-B/C/Dであり未実装',text)
   for dest in re.findall(r'\]\(([^)]+)\)',text):
    path=dest.split('#')[0]
    if path and '://' not in path:self.assertTrue((f.parent/path).exists(),str(f.relative_to(root))+':'+path)
  text=(root/'contracts/README.md').read_text().split('## Artifact Delivery v1.1',1)[1]
  for term in ['P-B','実装済み','P-C','P-D','未実施','定期実運用の完了を意味しない']:self.assertIn(term,text)
 def test_workflow_has_no_schedule_or_collector_execution(self):
  s=(root/'.github/workflows/validate.yml').read_text()
  self.assertNotRegex(s,r'(?m)^\s*(schedule|workflow_dispatch):')
  self.assertNotIn('scripts/knowledge_collector.py',s)
  self.assertIn('python -m unittest discover -s tests -v',s)
 def test_new_regression_detects_old_overview_without_product_edit(self):
  spec=importlib.util.spec_from_file_location('regression',root/'tests/test_knowledge_collector.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  test=m.CollectorTests('test_documented_pb_scope_is_consistent')
  before=Path(os.environ['PB_BEFORE']);oldroot=c.ROOT
  try:
   c.ROOT=before
   with self.assertRaises(AssertionError):test.test_documented_pb_scope_is_consistent()
  finally:c.ROOT=oldroot
  test.test_documented_pb_scope_is_consistent()
if __name__=='__main__':unittest.main(verbosity=2)
