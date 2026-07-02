"""uaa_remote.py — talk to a running Unreal Editor from outside it.

Unreal Engine's Python plugin ships a feature called *remote execution*:
the editor listens on a UDP multicast group for discovery pings, then opens
a TCP connection back to this client so we can send it Python commands and
read back everything they print.

This file is a small, self-contained, original implementation of that
protocol (standard library only — nothing to install).

To enable the editor side (one time, per project):
    Edit -> Project Settings -> Plugins -> Python -> check "Remote Execution"
    then restart the editor.

You normally don't use this module directly — `tools/ue.py` wraps it with
friendly commands like `doctor`, `read-blueprint` and `screenshot`.
"""

import json
import socket
import struct
import time
import uuid

PROTOCOL_VERSION = 1
PROTOCOL_MAGIC = "ue_py"

# These defaults match the Python plugin's default project settings.
# If you changed them in Project Settings -> Plugins -> Python, change them here too.
MULTICAST_GROUP = ("239.0.0.1", 6766)
MULTICAST_BIND = "127.0.0.1"
COMMAND_ENDPOINT = ("127.0.0.1", 6776)
RECV_SIZE = 8192

# Execution modes understood by the editor.
MODE_FILE = "ExecuteFile"            # run a multi-statement script (our default)
MODE_STATEMENT = "ExecuteStatement"  # run a single statement, print the result
MODE_EVAL = "EvaluateStatement"      # evaluate one expression, return its value

# Our in-editor scripts print their result as JSON between these two lines so
# the client can find it in the middle of whatever else the editor logs.
RESULT_BEGIN = "UAA_RESULT_BEGIN"
RESULT_END = "UAA_RESULT_END"


class UnrealNotFoundError(RuntimeError):
    """No running Unreal Editor answered on the multicast group."""


class UnrealConnection:
    """Discovers a running editor and runs Python inside it.

    Usage:
        with UnrealConnection() as ue:
            info = ue.discover()           # {'engine_version': ..., 'project_name': ...}
            result = ue.run("import unreal; print(unreal.SystemLibrary.get_engine_version())")
    """

    def __init__(self, multicast_group=MULTICAST_GROUP, bind_address=MULTICAST_BIND,
                 command_endpoint=COMMAND_ENDPOINT):
        self.node_id = str(uuid.uuid4())
        self.multicast_group = multicast_group
        self.bind_address = bind_address
        self.command_endpoint = command_endpoint
        self.editor = None  # filled by discover(): the editor's pong data + node_id
        self._udp = None
        self._tcp = None

    # ------------------------------------------------------------------ #
    # protocol plumbing
    # ------------------------------------------------------------------ #

    def _make_message(self, msg_type, dest=None, data=None):
        msg = {
            "version": PROTOCOL_VERSION,
            "magic": PROTOCOL_MAGIC,
            "type": msg_type,
            "source": self.node_id,
        }
        if dest is not None:
            msg["dest"] = dest
        if data is not None:
            msg["data"] = data
        return json.dumps(msg).encode("utf-8")

    def _parse_message(self, raw):
        """Decode one protocol message addressed to us, or None."""
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(msg, dict) or msg.get("magic") != PROTOCOL_MAGIC:
            return None
        if msg.get("version") != PROTOCOL_VERSION:
            return None
        if msg.get("source") == self.node_id:
            return None  # our own broadcast echoed back to us
        dest = msg.get("dest")
        if dest is not None and dest != self.node_id:
            return None
        return msg

    def _open_udp(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        udp.bind((self.bind_address, self.multicast_group[1]))
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
        membership = struct.pack(
            "=4s4s",
            socket.inet_aton(self.multicast_group[0]),
            socket.inet_aton(self.bind_address),
        )
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        return udp

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def discover(self, timeout=5.0):
        """Ping the multicast group until a running editor answers.

        Returns the editor's info dict (engine_version, project_name,
        project_root, user, machine, node_id). Raises UnrealNotFoundError
        if nothing answers within `timeout` seconds.
        """
        if self._udp is None:
            self._udp = self._open_udp()
        self._udp.settimeout(0.25)
        deadline = time.time() + timeout
        last_ping = 0.0
        while time.time() < deadline:
            now = time.time()
            if now - last_ping >= 1.0:
                self._udp.sendto(self._make_message("ping"), self.multicast_group)
                last_ping = now
            try:
                raw, _addr = self._udp.recvfrom(RECV_SIZE)
            except socket.timeout:
                continue
            msg = self._parse_message(raw)
            if msg and msg.get("type") == "pong":
                self.editor = dict(msg.get("data") or {})
                self.editor["node_id"] = msg["source"]
                return self.editor
        raise UnrealNotFoundError(
            "No running Unreal Editor answered within {:.0f}s.\n"
            "Checklist:\n"
            "  1. Is the Unreal Editor actually open, with your project loaded?\n"
            "  2. Is 'Remote Execution' checked? (Edit -> Project Settings -> Plugins -> Python)\n"
            "  3. Did you restart the editor after checking it?\n"
            "  4. If a firewall prompt appeared for UnrealEditor, did you click Allow?".format(timeout)
        )

    def connect(self, timeout=5.0):
        """Open the TCP command channel (the editor connects back to us)."""
        if self.editor is None:
            self.discover(timeout=timeout)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(self.command_endpoint)
        listener.listen(1)
        listener.settimeout(timeout)
        data = {
            "command_ip": self.command_endpoint[0],
            "command_port": self.command_endpoint[1],
        }
        self._udp.sendto(
            self._make_message("open_connection", dest=self.editor["node_id"], data=data),
            self.multicast_group,
        )
        try:
            self._tcp, _addr = listener.accept()
        except socket.timeout:
            raise UnrealNotFoundError(
                "Found the editor, but it never opened the command connection. "
                "Another remote-execution client may already be attached, or port "
                "{} is blocked/in use. Close other clients and try again.".format(self.command_endpoint[1])
            )
        finally:
            listener.close()

    def run(self, python_source, exec_mode=MODE_FILE, timeout=180.0):
        """Run Python source inside the editor and wait for the result.

        Returns the editor's result dict:
            {'success': bool, 'result': str,
             'output': [{'type': 'Info'|'Warning'|'Error', 'output': str}, ...]}
        """
        if self._tcp is None:
            self.connect()
        payload = {"command": python_source, "unattended": True, "exec_mode": exec_mode}
        self._tcp.sendall(self._make_message("command", dest=self.editor["node_id"], data=payload))
        self._tcp.settimeout(timeout)
        buf = b""
        while True:
            chunk = self._tcp.recv(RECV_SIZE)
            if not chunk:
                raise ConnectionError("Unreal closed the command connection before answering.")
            buf += chunk
            msg = self._parse_message(buf)  # None until the JSON is complete
            if msg and msg.get("type") == "command_result":
                return msg.get("data") or {}

    def close(self):
        if self._udp is not None and self.editor is not None:
            try:
                self._udp.sendto(
                    self._make_message("close_connection", dest=self.editor["node_id"]),
                    self.multicast_group,
                )
            except OSError:
                pass
        for sock in (self._tcp, self._udp):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self._tcp = None
        self._udp = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


# ---------------------------------------------------------------------- #
# helpers used by tools/ue.py
# ---------------------------------------------------------------------- #

def inject_params(python_source, params):
    """Prepend a PARAMS payload so in-editor scripts can read their arguments."""
    header = "UAA_PARAMS_JSON = {}\n".format(json.dumps(json.dumps(params or {})))
    return header + python_source


def output_text(result):
    """Everything the in-editor script printed, as one string."""
    return "".join(entry.get("output", "") for entry in (result.get("output") or []))


def output_errors(result):
    """Only the lines the editor logged as errors."""
    return [entry.get("output", "").rstrip()
            for entry in (result.get("output") or [])
            if entry.get("type") == "Error"]


def extract_result(result):
    """Parse the JSON blob printed between UAA_RESULT_BEGIN/END markers.

    Returns the decoded object, or None if the script never printed one.
    """
    text = output_text(result)
    start = text.find(RESULT_BEGIN)
    end = text.find(RESULT_END)
    if start == -1 or end == -1 or end <= start:
        return None
    blob = text[start + len(RESULT_BEGIN):end].strip()
    try:
        return json.loads(blob)
    except ValueError:
        return None
