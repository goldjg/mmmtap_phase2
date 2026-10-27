"""Allow CLI runtime children, deny namespace/admin/inspection escape.

This applies only to the versioned lower-assurance CLI profile. The original
strict worker/filter remains byte-for-byte unchanged.
"""
import ctypes
import errno
import os
import resource
import sys


def install():
    lib = ctypes.CDLL(None, use_errno=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if lib.prctl(38, 1, 0, 0, 0):
        raise RuntimeError("no_new_privileges_unavailable")
    sc = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    sc.seccomp_init.argtypes = [ctypes.c_uint32]; sc.seccomp_init.restype = ctypes.c_void_p
    sc.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    sc.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    sc.seccomp_load.argtypes = [ctypes.c_void_p]; sc.seccomp_release.argtypes = [ctypes.c_void_p]
    context = sc.seccomp_init(0x7fff0000)
    if not context: raise RuntimeError("CLI_seccomp_initialisation_failed")
    try:
        for name in ("unshare", "setns", "mount", "umount2", "ptrace", "bpf", "perf_event_open", "keyctl",
                     "open_by_handle_at", "process_vm_readv", "process_vm_writev", "kexec_load", "reboot"):
            number = sc.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and sc.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0):
                raise RuntimeError("CLI_seccomp_rule_failed")
        if sc.seccomp_load(context): raise RuntimeError("CLI_seccomp_load_failed")
    finally:
        sc.seccomp_release(context)


if __name__ == "__main__":
    install()
    os.execv(sys.argv[1], sys.argv[1:])
