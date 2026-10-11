"""Same-attempt final integration probes, synthetic only; no implementation changes."""
import os,sys,unittest,copy,tempfile,subprocess,importlib.util
from pathlib import Path
from unittest.mock import patch
root=Path(os.environ['PB_HEAD']);prior=Path(os.environ['PB_PRIOR_CASES'])
spec=importlib.util.spec_from_file_location('prior',prior);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);c=p.c
class Final(unittest.TestCase):
 def test_conflict_resolutions_preserve_entire_prior_documents(self):
  old=Path(os.environ['PB_PREVIOUS'])
  suffixes={'README.md':'\nFixed cross-repository delivery and immutable candidate/tree verification use [Delivery 1.2](contracts/cross-reference-delivery.md). [Reproduction instructions](examples/crossref-delivery/README.md) separate record preparation from Manager-authorized consumption.\n','contracts/README.md':'\n## Delivery 1.2 cross references\n\nSee [the versioned extension](cross-reference-delivery.md) for typed Git commit objects, canonical cross-repository blobs, immutable candidate profiles and complete tree snapshots. Transport integrity is separate from approval and semantic review.\n'}
  for name,suffix in suffixes.items():self.assertEqual((root/name).read_text(),(old/name).read_text()+suffix)
 def test_collector_keeps_explicit_delivery11_binding(self):
  src=p.Memory();state=c.initial('SYNTHETIC','synthetic/final')
  real=c.verify_handoffs
  with patch.object(c,'verify_handoffs',wraps=real) as verify:
   new,archive=c.scan(state,c.encode(src.registry),src)
  self.assertEqual(verify.call_args.args[2],'1.1');self.assertEqual({x['status'] for x in new['events'].values()},{'verified'})
 def test_collector_does_not_implicitly_adopt_delivery12_refs(self):
  src=p.Memory();state=c.initial('SYNTHETIC','synthetic/final')
  for mode in ['version','object_type']:
   reg=copy.deepcopy(src.registry)
   if mode=='version':reg['schema_version']='1.2'
   else:reg['artifacts'][0]['reference']['object_type']='git-blob'
   with self.assertRaises(ValueError):c.scan(state,c.encode(reg),src)
  self.assertEqual(state,c.initial('SYNTHETIC','synthetic/final'))
 def test_snapshot_reader_rejects_equal_length_corrupted_blob(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Path(tmp)/'repo';repo.mkdir()
   def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL)
   git('init','-q');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid');(repo/'inbox').mkdir();(repo/'inbox/f').write_bytes(b'SYNTHETIC bytes');git('add','.');git('commit','-qm','synthetic');sha=git('rev-parse','HEAD').decode().strip()
   source=c.SnapshotSource(Path(tmp)/'cache');source.repositories['synthetic/repo',sha]=repo;refs=source.enumerate(dict(repository='synthetic/repo',commit=sha,inbox_path='inbox'));self.assertEqual(len(refs),1);self.assertEqual(source.read(refs[0]),b'SYNTHETIC bytes');real=source.git
   def corrupted(directory,*args):
    raw=real(directory,*args)
    return b'X'+raw[1:] if args[:2]==('cat-file','blob') else raw
   with patch.object(source,'git',side_effect=corrupted),self.assertRaises(ValueError):source.read(refs[0])
if __name__=='__main__':unittest.main(verbosity=2)
