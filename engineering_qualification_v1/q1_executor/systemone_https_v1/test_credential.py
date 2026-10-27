"""Secret guard and sealed binding checks; no operator credential reads."""
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from .credential import EntityGuard, binding, validate
from .contract import make_manifest
from ..model import decode, digest, encode, validate_manifest


class CredentialTests(unittest.TestCase):
    def test_wrong_kernel_sender_cannot_release_or_consume_source(self):
        script = '''import array,os,socket,struct
from engineering_qualification_v1.q1_executor.systemone_https_v1.credential import READY,handoff_from_environment
parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
parent.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
read_fd,write_fd=os.pipe()
try:
 try:
  child.sendmsg([READY],[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',os.getpid()+1000000,os.getuid(),os.getgid()))])
 except PermissionError:pass
 else:raise AssertionError('kernel allowed forged sender PID')
 child.sendmsg([READY],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[write_fd]))])
 try:handoff_from_environment(parent,os.getpid()+1000000)
 except ValueError as exc:assert str(exc)=='credential_broker_sender_not_authenticated'
 else:raise AssertionError('unrelated sender accepted')
 assert 'JEVKEY' in os.environ
 os.set_blocking(read_fd,False)
 try:os.read(read_fd,1)
 except BlockingIOError:pass
 else:raise AssertionError('source released to unauthenticated channel')
 print('REFUSED_WITHOUT_SOURCE_CONSUMPTION')
finally:
 os.close(read_fd);os.close(write_fd);child.close()
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True,
                                env={"LANG": "C.UTF-8", "JEVKEY": "DUMMY-NOT-AN-OPERATOR-KEY"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), b"REFUSED_WITHOUT_SOURCE_CONSUMPTION")

    def test_all_read_boundaries_refuse_raw_and_JSON_escaped_reflections(self):
        token = bytearray(b"DUMMY-JEVKEY-never-a-real-key")
        for value in (bytes(token), b"".join(("\\u%04x" % c).encode() for c in token),
                      b"DUMMY-\\u004aEVKEY-never-a-real-key"):
            raw = b'{"error":"' + value + b'"}'
            for boundary in range(len(raw) + 1):
                guard = EntityGuard(token)
                saved = bytearray()
                with self.assertRaisesRegex(ValueError, "credential_reflection_capture_refused"):
                    saved.extend(guard.feed(raw[:boundary]))
                    saved.extend(guard.feed(raw[boundary:]))
                    saved.extend(guard.feed(b"", final=True))
                self.assertNotIn(token, saved)
                self.assertNotIn(value, saved)

    def test_safe_entity_remains_exact_with_escapes_and_one_byte_reads(self):
        raw = b' \n{"note":"a\\nslash\\/unicode\\u0041","number":0.1234500}\n'
        guard = EntityGuard(bytearray(b"DUMMY-JEVKEY"))
        captured = b"".join(guard.feed(bytes([c])) for c in raw) + guard.feed(b"", final=True)
        self.assertEqual(captured, raw)

    def test_bearer_validation_rejects_header_injection_without_echo(self):
        for value in (b"", b"DUMMY\r\nInjected:x", b"a b", b"bad\x00key", b"=bad", b"a=b", b"X" * 4093):
            with self.subTest(size=len(value)), self.assertRaisesRegex(ValueError, "JEVKEY_invalid_or_out_of_bounds"):
                validate(bytearray(value))
        validate(bytearray(b"DUMMY-valid+/~.key=="))

    def test_rehashed_credential_policy_escalation_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_manifest(Path(temp) / "fixture", jevkey=True)
            m, _ = validate_manifest(root)
            m["https_qualification"]["credential_binding"]["worker_access"] = "allowed"
            m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
            (root / "manifest.json").write_bytes(encode(m))
            with self.assertRaisesRegex(ValueError, "JEVKEY_broker_binding_changed"):
                validate_manifest(root)


if __name__ == "__main__":
    unittest.main()
