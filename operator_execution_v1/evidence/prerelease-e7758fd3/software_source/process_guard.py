"""Trusted in-namespace launcher: deny child processes, retain runtime threads.

This is not a universal no-code-execution sandbox. The CLI itself still runs
code, can read its own credential and can use the permitted network namespace.
"""
from __future__ import annotations

import ctypes
import errno
import os
import sys


class Comparison(ctypes.Structure):
    _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_uint),
                ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]


def install() -> None:
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_load.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("seccomp_initialization_failed")
    try:
        for name in ("fork", "vfork", "clone", "clone3", "unshare", "setns", "ptrace"):
            number = library.seccomp_syscall_resolve_name(name.encode())
            if number < 0:
                if name in ("fork", "vfork"):
                    continue
                raise RuntimeError("seccomp_syscall_unavailable:" + name)
            # clone3 falls back to clone, whose thread flag can be inspected by BPF.
            action = 0x00050000 | (errno.ENOSYS if name == "clone3" else errno.EPERM)
            compare = Comparison(0, 7, 0x00010000, 0) if name == "clone" else None
            result = library.seccomp_rule_add_array(context, action, number, int(compare is not None),
                                                   ctypes.pointer(compare) if compare else None)
            if result != 0:
                raise RuntimeError("seccomp_rule_failed:" + name)
        if library.seccomp_load(context) != 0:
            raise RuntimeError("seccomp_load_failed")
    finally:
        library.seccomp_release(context)


def main() -> int:
    if len(sys.argv) < 2:
        raise ValueError("An explicitly pinned command is required")
    install()
    os.execv(sys.argv[1], sys.argv[1:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
