"""Offline platform observations and a benign unfiltered fork control."""
import ctypes
import json
import os
import platform
import subprocess

lib = ctypes.CDLL(None, use_errno=True)
abi = lib.syscall(444, 0, 0, 1)
landlock_error = ctypes.get_errno()
net = subprocess.run(["/usr/bin/bwrap", "--unshare-all", "--ro-bind", "/usr", "/usr",
                      "--symlink", "usr/lib", "/lib", "--", "/usr/bin/true"], capture_output=True)
base = ["/usr/bin/bwrap", "--unshare-user", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
        "--die-with-parent", "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/bin", "/bin", "--proc", "/proc",
        "--dev", "/dev", "--tmpfs", "/work", "--chdir", "/work", "--"]
code = "import os; p=os.fork(); os._exit(0) if p==0 else None; os.waitpid(p,0); print('fork_allowed_without_inner_seccomp')"
control = subprocess.run(base + ["/usr/bin/python3.11", "-I", "-S", "-B", "-c", code], capture_output=True,
                         env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
result = {"classification": "OFFLINE ENGINEERING PLATFORM PROBES; NO PROVIDER CALLS",
          "platform": platform.platform(), "machine": platform.machine(),
          "landlock": {"abi": abi, "errno": landlock_error,
                       "status": "UNAVAILABLE" if abi < 1 else "AVAILABLE_NOT_USED"},
          "network_namespace_setup": {"exit": net.returncode, "stderr": net.stderr.decode(),
                                      "status": "UNAVAILABLE" if net.returncode else "AVAILABLE_NOT_USED"},
          "namespace_without_inner_seccomp": {"exit": control.returncode, "stdout": control.stdout.decode(),
                                               "stderr": control.stderr.decode()},
          "network_control_used": "irreversible native seccomp default-deny allowlist; no sockets admitted",
          "real_provider_calls": 0}
print(json.dumps(result, indent=2, sort_keys=True))
if control.returncode or control.stdout.strip() != b"fork_allowed_without_inner_seccomp":
    raise SystemExit(1)
