import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from completion_fixture import build, save, write, NOW, encode
from scripts.validate_issue_completion import Bundle, validate_files, instant, sha, validate_handoff_pair


class BindingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.a,self.c=build(self.root)

    def validate(self, pin=None):
        return validate_files(self.root/'completion.json',self.root/'context.json',pin or self.a['context_sha256'],self.root/'handoff.json',now=instant(NOW))

    def test_context_independent_pin_and_raw_whitespace(self):
        with self.assertRaisesRegex(ValueError,'pin'): self.validate('0'*64)
        p=self.root/'context.json'; p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'pin'): self.validate()

    def test_strict_json_all_entrypoints(self):
        payloads=[b'{"a":1,"a":2}',b'{"a":1,"\\u0061":2}',b'{"a":NaN}',b'{"a":Infinity}',b'\xef\xbb\xbf{}',b'{} {}',b'\xff']
        for name in ('completion.json','context.json','handoff.json'):
            for raw in payloads:
                with self.subTest(name=name,raw=raw):
                    self.a,self.c=build(self.root); (self.root/name).write_bytes(raw)
                    with self.assertRaises((ValueError,UnicodeError)): self.validate()

    def test_wrong_hash_size_missing_source_and_one_byte(self):
        for case in ('hash','size','missing','byte'):
            with self.subTest(case=case):
                self.a,self.c=build(self.root); ref=self.a['evidence'][-1]['source_ref']; path=self.root/ref['locator']
                if case=='hash': ref['sha256']='0'*64; write(self.root,'completion.json',self.a)
                elif case=='size': ref['size']+=1; write(self.root,'completion.json',self.a)
                elif case=='missing': path.unlink()
                else: path.write_bytes(path.read_bytes()+b'\n')
                with self.assertRaises(ValueError): self.validate()

    def test_remote_escape_absolute_symlink_refs(self):
        for locator in ('https://example.invalid/record','../outside','/tmp/outside','a/../scope.txt','./scope.txt','linked.txt'):
            with self.subTest(locator=locator):
                self.a,self.c=build(self.root)
                if locator=='linked.txt': (self.root/locator).symlink_to(self.root/'scope.txt')
                self.a['evidence'][-1]['source_ref']['locator']=locator
                write(self.root,'completion.json',self.a)
                with self.assertRaises(ValueError): self.validate()

    def test_read_time_swap_detected(self):
        original=Bundle.finish
        def swap(bundle):
            p=self.root/'scope.txt'; p.write_bytes(p.read_bytes()+b'changed')
            return original(bundle)
        with patch.object(Bundle,'finish',swap):
            with self.assertRaisesRegex(ValueError,'changed'): self.validate()

    def test_handoff_same_bytes_other_path_rejected(self):
        p=self.root/'completion.json'; (self.root/'copy.json').write_bytes(p.read_bytes())
        h=json.loads((self.root/'handoff.json').read_bytes()); h['artifacts'][0]['locator']='copy.json'
        write(self.root,'handoff.json',h)
        with self.assertRaisesRegex(ValueError,'evaluated file'): self.validate()

    def test_handoff_final_evidence_same_bytes_other_path_rejected(self):
        h=json.loads((self.root/'handoff.json').read_bytes()); ref=h['artifacts'][1]
        (self.root/'copy.json').write_bytes((self.root/ref['locator']).read_bytes()); ref['locator']='copy.json'
        write(self.root,'handoff.json',h)
        with self.assertRaisesRegex(ValueError,'same measurement bytes'): self.validate()

    def test_handoff_role_issue_originals_artifact_and_final(self):
        for case in ('role','issue','original','artifact','final','outcome'):
            with self.subTest(case=case):
                self.a,self.c=build(self.root); h=json.loads((self.root/'handoff.json').read_bytes())
                if case=='role': h['role']='implementation'
                elif case=='issue': h['issue']['id']='other'
                elif case=='original': h['issue']['acceptance_criteria'][0]['verbatim']+=' changed'
                elif case=='artifact': h['artifacts'][0]['revision']='sha256:'+'0'*64
                elif case=='final': h.pop('final_assessment')
                else: h['final_assessment']['outcome']='unverified'
                write(self.root,'handoff.json',h)
                with self.assertRaises(ValueError): self.validate()

    def test_pairing_initial_bytes_vs_evaluated_object(self):
        raw=(self.root/'completion.json').read_bytes(); self.a['reasons']=['altered object']
        with self.assertRaisesRegex(ValueError,'initial bytes'):
            validate_handoff_pair(self.a,json.loads((self.root/'handoff.json').read_bytes()),Bundle(self.root),self.root/'completion.json',self.root/'handoff.json',raw)

    def test_pr_handoff_cannot_be_issue_final(self):
        # A PR's v1 assessment stays unverified even though the separate aggregate achieves.
        from scripts.validate_readiness import validate_handoff_pair as pair
        p=self.root/'app-readiness.json'; r=json.loads(p.read_bytes()); h=json.loads((self.root/'handoff.json').read_bytes())
        self.assertTrue(pair(r,h,readiness_bytes=p.read_bytes(),readiness_path=p,handoff_path=self.root/'handoff.json'))

    def test_no_context_authority_from_assessment_itself(self):
        altered=copy.deepcopy(self.c); altered['scope_decisions'][1]['status']='revoked'
        raw=encode(altered); (self.root/'context.json').write_bytes(raw)
        # Matching declarations inside documents cannot override the operator's old pin.
        self.a['context_sha256']=sha(raw); write(self.root,'completion.json',self.a)
        with self.assertRaises(ValueError): self.validate(sha(encode(self.c)))

    def test_blob_id_identity_collision(self):
        self.a['evidence'][-1]['source_ref']['id']=self.a['evidence'][0]['source_ref']['id']
        write(self.root,'completion.json',self.a)
        with self.assertRaisesRegex(ValueError,'ID reused'): self.validate()


if __name__=='__main__': unittest.main()
