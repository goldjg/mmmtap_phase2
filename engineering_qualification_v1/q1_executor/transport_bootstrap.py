"""Trusted standalone bootstrap, mounted read-only; no repository imports.

Runs only inside the mount/PID/user/IPC/UTS namespace. Apply an irreversible
native-architecture seccomp allowlist BEFORE evaluating the adapter bytes.
Missing controls abort before adapter execution. No live adapter is packaged.
"""
import ctypes
import hashlib
import json
import os
import resource
import signal
import sys
import time

VERSION = "q1-offline-subprocess-v1"
# All other syscalls, including fork/clone/exec, sockets, ptrace, process_vm,
# io_uring, mounts, namespace changes and privilege APIs, return EPERM.
ALLOWED = ("read", "write", "close", "fstat", "newfstatat", "statx", "lseek", "pread64",
           "openat", "getdents64", "readlink", "readlinkat", "access", "faccessat",
           "faccessat2", "getcwd", "brk", "mmap", "mprotect", "munmap", "mremap",
           "madvise", "futex", "clock_gettime", "clock_nanosleep", "nanosleep",
           "getrandom", "getpid", "getppid", "gettid", "getuid", "geteuid", "getgid",
           "getegid", "uname", "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
           "sigaltstack", "fcntl", "fsync", "fdatasync", "ftruncate", "exit", "exit_group")


def main():
    envelope_raw = open("/inputs/envelope.json", "rb").read()
    request_raw = open("/inputs/request.json", "rb").read()
    adapter_raw = open("/inputs/adapter.py", "rb").read()
    envelope = json.loads(envelope_raw)
    if (envelope["contract"] != VERSION or envelope["network"] != "denied"
            or envelope["tools"] != "denied"
            or hashlib.sha256(request_raw).hexdigest() != envelope["request_sha256"]
            or hashlib.sha256(adapter_raw).hexdigest() != envelope["adapter_sha256"]
            or dict(os.environ) != {"HOME": "/home/assessor", "LANG": "C.UTF-8", "PATH": "/usr/bin:/bin",
                                    "TMPDIR": "/work", "PWD": "/work"}
            or os.getcwd() != "/work"):
        raise ValueError("bootstrap_sealed_context_mismatch")
    # Kill the adapter if its bwrap supervisor dies; also set in the host wrapper.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or libc.prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "pdeathsig_or_no_new_privs")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    lib = ctypes.CDLL(envelope["seccomp_library"])
    lib.seccomp_init.argtypes = [ctypes.c_uint32]; lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x00050000 | 1)  # default ERRNO(EPERM), not a denylist.
    if not ctx:
        raise RuntimeError("seccomp_init_failed")
    for name in ALLOWED:
        number = lib.seccomp_syscall_resolve_name(name.encode())
        if number >= 0 and lib.seccomp_rule_add(ctx, 0x7fff0000, number, 0) != 0:
            raise RuntimeError("seccomp_rule_failed:" + name)
    if lib.seccomp_load(ctx) != 0:
        raise RuntimeError("seccomp_load_failed")
    lib.seccomp_release(ctx)
    os.write(2, json.dumps({"bootstrap": VERSION, "request_sha256": envelope["request_sha256"],
                            "attempt_id": envelope["attempt_id"], "seccomp_loaded": True}).encode() + b"\n")
    # No inherited application modules, sessions, repository cwd or user site.
    namespace = {"__name__": "__main__", "sealed_request": request_raw,
                 "sealed_envelope": envelope}
    exec(compile(adapter_raw, "/inputs/adapter.py", "exec"), namespace)


if __name__ == "__main__":
    main()
