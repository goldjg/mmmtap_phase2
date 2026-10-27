"""Offline OS controls. These do not qualify a production network deployment."""
import ctypes
import errno
import os
import socket


def restrict_to_fixture(route):
    if (os.readlink("/proc/self/ns/net") != route["network_namespace"]
            or sorted(name for _, name in socket.if_nameindex()) != route.get("interfaces", ["lo"])):
        raise ValueError("BLOCKED_private_loopback_network_namespace_required")
    # Inspect the complete kernel ruleset, not a caller-supplied policy label.
    import subprocess
    from ..model import decode, digest
    actual = decode(subprocess.check_output(["/usr/sbin/nft", "-j", "-s", "list", "ruleset"], env={"LANG": "C.UTF-8"}))
    actual = [{k: {a: b for a, b in v.items() if a != "handle"}} for item in actual["nftables"]
              for k, v in item.items() if k != "metainfo"]
    expected = expected_rules(route["port"], route["address"])
    if actual != expected:
        raise ValueError("BLOCKED_exact_kernel_destination_rules_required")
    lib = ctypes.CDLL(None, use_errno=True)
    if lib.prctl(38, 1, 0, 0, 0):
        raise ValueError("BLOCKED_no_new_privileges")
    # Remove namespace administration authority before any network activity.
    class Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]
    class Cap(ctypes.Structure):
        _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32), ("inheritable", ctypes.c_uint32)]
    for cap in range(41):
        lib.prctl(24, cap, 0, 0, 0)
    if lib.capset(ctypes.byref(Header(0x20080522, 0)), ctypes.byref((Cap * 2)())):
        raise ValueError("BLOCKED_capability_drop")
    return {"network_namespace": route["network_namespace"], "interfaces": route.get("interfaces", ["lo"]),
            "kernel_policy": "nftables_default_drop_exact_IP_TCP_port", "rules_sha256": digest(expected),
            "allowed_address": route["address"], "allowed_TCP_connect_port": route["port"], "capabilities_dropped": True}


def close_network_creation(library):
    # One already-connected TCP descriptor remains. No socket/connect, DNS,
    # subprocess, namespace, ioctl, io_uring or alternate egress can be created.
    from ..transport_bootstrap import ALLOWED
    lib = ctypes.CDLL(library)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]; lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]; lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x00050000 | errno.EPERM)
    if not ctx:
        raise ValueError("BLOCKED_transport_seccomp_init")
    extra = ("poll", "ppoll", "select", "pselect6", "recvfrom", "sendto", "recvmsg", "sendmsg",
             "getsockname", "getpeername", "getsockopt", "setsockopt", "shutdown", "setitimer",
             "pwrite64", "unlink", "unlinkat")  # trusted broker's existing durable SQLite journal.
    try:
        for name in (*ALLOWED, *extra):
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and lib.seccomp_rule_add(ctx, 0x7fff0000, number, 0):
                raise ValueError("BLOCKED_transport_seccomp_rule")
        class Compare(ctypes.Structure):
            _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_uint),
                        ("a", ctypes.c_uint64), ("b", ctypes.c_uint64)]
        lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                               ctypes.c_uint, ctypes.POINTER(Compare)]
        # Python's TLS wrapper sets nonblocking mode on the existing descriptor.
        # This grants FIONBIO only, not network-administration ioctls.
        comparison = Compare(1, 4, 0x5421, 0)
        if lib.seccomp_rule_add_array(ctx, 0x7fff0000, lib.seccomp_syscall_resolve_name(b"ioctl"),
                                      1, ctypes.byref(comparison)):
            raise ValueError("BLOCKED_transport_FIONBIO_rule")
        if lib.seccomp_load(ctx):
            raise ValueError("BLOCKED_transport_seccomp_load")
    finally:
        lib.seccomp_release(ctx)


def adversarial_probes(route):
    """Actual syscalls in a separate restricted process; no remote addresses."""
    evidence = restrict_to_fixture(route)
    checks = {}
    other = "127.0.0.2" if route["address"] == "127.0.0.1" else "127.0.0.1"
    for name, host, port in (("other_local_port", route["address"], route["port"] + 1 if route["port"] < 65535 else 1024),
                             ("other_address_same_port", other, route["port"]),
                             ("provider_port_443", route["address"], 443)):
        with socket.socket() as sock:
            sock.settimeout(0.15)
            try:
                sock.connect((host, port))
                checks[name] = "UNEXPECTED_ALLOWED"
            except TimeoutError:
                checks[name] = "kernel_drop_timeout"
            except OSError as exc:
                checks[name] = exc.errno
    if set(checks.values()) != {"kernel_drop_timeout"}:
        raise AssertionError(checks)
    evidence["kernel_connect_denials"] = checks
    return evidence


def expected_rules(port, address="127.0.0.1"):
    rule = {"family": "inet", "table": "q1_https", "chain": "output"}
    return [
        {"table": {"family": "inet", "name": "q1_https"}},
        {"chain": {"family": "inet", "table": "q1_https", "name": "output", "type": "filter", "hook": "output", "prio": 0, "policy": "drop"}},
        {"rule": {**rule, "expr": [{"match": {"op": "in", "left": {"ct": {"key": "state"}}, "right": "established"}}, {"accept": None}]}},
        {"rule": {**rule, "expr": [
            {"match": {"op": "==", "left": {"payload": {"protocol": "ip", "field": "daddr"}}, "right": address}},
            {"match": {"op": "==", "left": {"payload": {"protocol": "tcp", "field": "dport"}}, "right": port}}, {"accept": None}]}},
        {"rule": {**rule, "expr": [{"counter": None}, {"drop": None}]}}]


def install_fixture_policy(port, address="127.0.0.1"):
    import subprocess
    # The caller already created an otherwise empty namespace. Only its own
    # qualification table is ever replaced; never modify host firewall rules.
    if sorted(name for _, name in socket.if_nameindex()) not in (["lo"], ["lo", "q1-client"]):
        raise ValueError("private_loopback_namespace_required")
    subprocess.run(["/usr/sbin/nft", "delete", "table", "inet", "q1_https"], capture_output=True)
    rules = ("table inet q1_https { chain output { type filter hook output priority 0; policy drop; "
             "ct state established accept; ip daddr " + address + " tcp dport " + str(port) + " accept; counter drop; }\n}\n")
    subprocess.run(["/usr/sbin/nft", "-f", "-"], input=rules.encode(), check=True, capture_output=True)
