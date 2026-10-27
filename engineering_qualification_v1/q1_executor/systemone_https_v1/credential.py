"""Existing JEVKEY convention, one broker-only anonymous-pipe handoff.

No provider SDK, login, key generation or persistent credential store. The
launcher reads its own JEVKEY only for an explicitly bound dispatch, after both
processes are non-dumpable. Qualification invokes it in a clean dummy-only child.
"""
import ctypes
import array
import os
import resource
import re
import select
import socket
import stat
import struct
import time

VERSION = "q1-broker-jevkey-fd-v1"
MAX_BYTES = 4092  # length prefix + token fits even a minimum-capacity pipe.
READY = b"Q1-JEVKEY-FD-READY\n"


def binding():
    return {"version": VERSION, "source": "JEVKEY", "delivery": "post-hardening-pipe-SCM_RIGHTS-authenticated-SCM_CREDENTIALS",
            "launcher_and_broker": "non-dumpable-hard-core-limit-zero", "worker_access": "denied",
            "credential_in_manifest_environment_argv_or_custody": False, "maximum_bytes": MAX_BYTES}


def configured():
    # Membership only: never obtain, print, hash or test the operator's value.
    return "JEVKEY" in os.environ


def harden():
    lib = ctypes.CDLL(None, use_errno=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if lib.prctl(4, 0, 0, 0, 0) or lib.prctl(3, 0, 0, 0, 0) != 0:
        raise ValueError("credential_process_protection_unavailable")
    if resource.getrlimit(resource.RLIMIT_CORE) != (0, 0):
        raise ValueError("credential_core_limit_unavailable")
    return {"dumpable": False, "core_soft": 0, "core_hard": 0}


def exact_read(fd, size, deadline):
    raw = bytearray()
    while len(raw) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise ValueError("credential_channel_deadline")
        piece = os.read(fd, size - len(raw))
        if not piece:
            raise ValueError("credential_channel_incomplete")
        raw.extend(piece)
    return raw


def write_all(fd, data):
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        view = view[count:]


def broker_ready(control_fd):
    if control_fd < 3:
        raise ValueError("credential_descriptor_invalid")
    protection = harden()
    # The actual credential pipe DOES NOT EXIST during exec/Python startup.
    # A stolen pre-hardening control endpoint cannot read this outgoing FD or
    # impersonate this PID in SCM_CREDENTIALS on the protected parent endpoint.
    channel = socket.socket(fileno=control_fd)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    try:
        channel.sendmsg([READY], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [write_fd]))])
    except BaseException:
        os.close(read_fd); raise
    finally:
        os.close(write_fd); channel.close()
    return read_fd, protection


def handoff_from_environment(channel, expected_pid, timeout=2, *, source=None):
    """Only runtime caller; tests run that caller in a clean dummy environment."""
    protection = harden()
    write_fd = None
    try:
        if source is None and not configured():
            raise ValueError("JEVKEY_not_configured")
        channel.settimeout(timeout)
        data, ancillary, flags, _ = channel.recvmsg(len(READY), socket.CMSG_SPACE(16) + socket.CMSG_SPACE(12), socket.MSG_CMSG_CLOEXEC)
        descriptors, peer = [], None
        for level, kind, payload in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                values = array.array("i"); values.frombytes(payload[:len(payload) - len(payload) % values.itemsize])
                descriptors.extend(values)
            elif level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                peer = struct.unpack("3i", payload)
        if (data != READY or flags & (socket.MSG_CTRUNC | socket.MSG_TRUNC) or len(descriptors) != 1
                or peer is None or peer[:2] != (expected_pid, os.getuid())):
            for fd in descriptors: os.close(fd)
            raise ValueError("credential_broker_sender_not_authenticated")
        write_fd = descriptors[0]
        if not stat.S_ISFIFO(os.fstat(write_fd).st_mode):
            raise ValueError("credential_anonymous_pipe_required")
        # Remove from this launcher's environment so later children cannot
        # inherit it. This does not mutate the operator's parent shell.
        if source is None:
            value = os.environ.pop("JEVKEY")
            try:
                token = bytearray(value.strip().encode("ascii"))
            except (UnicodeError, AttributeError):
                raise ValueError("JEVKEY_invalid_encoding") from None
            del value
        else:
            # Invoked only AFTER kernel sender authentication above. The
            # campaign launcher retains its protected in-memory source, never
            # an environment variable or an inherited credential descriptor.
            token = source()
        try:
            validate(token)
            write_all(write_fd, struct.pack("!I", len(token)))
            write_all(write_fd, token)
        finally:
            token[:] = b"\x00" * len(token)
        return {"contract": VERSION, "source_configured": True, "broker_ready_before_release": True,
                "broker_sender_PID_authenticated": True,
                "launcher_protection": protection, "delivery": "single_use_pipe_written_and_closed"}
    finally:
        if write_fd is not None: os.close(write_fd)
        channel.close()


def validate(token):
    # Historical Bearer header semantics, with control/header injection refused.
    if not 1 <= len(token) <= MAX_BYTES or re.fullmatch(rb"[A-Za-z0-9._~+/-]+=*", token) is None:
        raise ValueError("JEVKEY_invalid_or_out_of_bounds")


def receive(fd):
    """Consume/close once, after TLS and policy checks; never inherited by tools."""
    if fd is None:
        raise ValueError("credential_descriptor_missing")
    try:
        deadline = time.monotonic() + 1
        length = struct.unpack("!I", exact_read(fd, 4, deadline))[0]
        if not 1 <= length <= MAX_BYTES:
            raise ValueError("credential_channel_size")
        token = exact_read(fd, length, deadline)
        validate(token)
        if exact_eof(fd, deadline) is not True:
            raise ValueError("credential_channel_trailing_data")
        return token
    finally:
        os.close(fd)


def exact_eof(fd, deadline):
    remaining = deadline - time.monotonic()
    return remaining > 0 and bool(select.select([fd], [], [], remaining)[0]) and os.read(fd, 1) == b""


class EntityGuard:
    """Archive exact safe prefixes; a credential reflection stops capture.

    Hold back enough bytes to detect matches spanning response reads BEFORE
    any complete credential can enter durable custody. Never forge a redacted
    provider entity or silently claim that refused bytes were captured.
    """
    def __init__(self, token):
        self.token = token
        self.pending = bytearray()

    def feed(self, piece, final=False):
        self.pending.extend(piece)
        # Decode JSON-style escapes before matching, including mixed literal/
        # unicode escapes across reads. Keep raw offsets; never rewrite custody.
        normal, starts, index, incomplete = bytearray(), [], 0, None
        escapes = {34: 34, 92: 92, 47: 47, 98: 8, 102: 12, 110: 10, 114: 13, 116: 9}
        while index < len(self.pending):
            start, value, width = index, self.pending[index], 1
            if value == 92:
                if index + 1 == len(self.pending):
                    incomplete = index; break
                following = self.pending[index + 1]
                if following == 117:
                    if index + 6 > len(self.pending):
                        incomplete = index; break
                    try:
                        code = int(self.pending[index + 2:index + 6], 16)
                        value, width = (code if code < 128 else 255), 6
                    except ValueError:
                        pass
                elif following in escapes:
                    value, width = escapes[following], 2
            normal.append(value); starts.append(start); index += width
        if self.token in normal:
            self.pending.clear()
            raise ValueError("credential_reflection_capture_refused")
        count = len(self.pending)
        if not final:
            if incomplete is not None:
                count = incomplete
            for size in range(min(len(normal), len(self.token) - 1), 0, -1):
                if normal.endswith(self.token[:size]):
                    count = min(count, starts[len(normal) - size]); break
        safe = bytes(self.pending[:count]); del self.pending[:count]
        return safe

    def clear(self):
        self.pending[:] = b"\x00" * len(self.pending); self.pending.clear()
