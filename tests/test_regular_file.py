import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from scripts.regular_file import read_regular, artifact_path, MAX_FILE


class RegularFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.file=self.root/'artifact';self.file.write_bytes(b'fixed')

    def test_regular_bounded(self):
        self.assertEqual(read_regular(self.file,limit=5),b'fixed')
        with self.assertRaises(ValueError): read_regular(self.file,limit=4)
        with self.assertRaises(ValueError): read_regular(self.file,limit=MAX_FILE+1)

    def test_fifo_socket_directory_symlink(self):
        fifo=self.root/'fifo';os.mkfifo(fifo)
        sock=socket.socket(socket.AF_UNIX);self.addCleanup(sock.close);sock.bind(str(self.root/'socket'))
        link=self.root/'link';link.symlink_to(self.file)
        ancestor=self.root/'ancestor';ancestor.symlink_to(self.root,target_is_directory=True)
        for path in (fifo,self.root/'socket',self.root,link,ancestor/'artifact',Path('/dev/null')):
            with self.subTest(path=path), self.assertRaises((OSError,ValueError)):
                read_regular(path)

    def test_unsafe_locator(self):
        for value in ('../artifact','/etc/passwd','a/../artifact','./artifact','a//b','a\\b','https://example.invalid/a'):
            with self.assertRaises(ValueError): artifact_path(self.root,value)

    def test_replacement_between_stat_and_open_nonblocking(self):
        original=os.open
        def swap(path,flags,*args,**kwargs):
            if path=='artifact':
                self.file.unlink();os.mkfifo(self.file)
            return original(path,flags,*args,**kwargs)
        with patch('scripts.regular_file.os.open',side_effect=swap), self.assertRaises(ValueError):
            read_regular(self.file)

    def test_replacement_growth_same_size_mutation_during_read(self):
        original=os.read
        for mode in ('replace','grow','same_size'):
            self.file.write_bytes(b'fixed'); done=False
            def mutate(fd,size):
                nonlocal done
                raw=original(fd,size)
                if not done:
                    done=True
                    if mode=='replace':
                        other=self.root/'other';other.write_bytes(b'fixed');other.replace(self.file)
                    else: self.file.write_bytes(b'changed' if mode=='grow' else b'other')
                return raw
            with patch('scripts.regular_file.os.read',side_effect=mutate),self.assertRaises(ValueError):
                read_regular(self.file,limit=5)

    def test_ancestor_replacement(self):
        sub=self.root/'sub';sub.mkdir();f=sub/'artifact';f.write_bytes(b'fixed')
        original=os.read;done=False
        def swap(fd,size):
            nonlocal done
            raw=original(fd,size)
            if not done:
                done=True;sub.rename(self.root/'old');sub.mkdir();(sub/'artifact').write_bytes(b'fixed')
            return raw
        with patch('scripts.regular_file.os.read',side_effect=swap), self.assertRaises(ValueError): read_regular(f)
