"""Exercise lifecycle failures with a tiny HTTP server; never load model weights."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_leanstral_ephemeral.py"
spec = importlib.util.spec_from_file_location("ephemeral", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class EphemeralTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.children = []
        self.model = self.root / "tiny.gguf"
        self.model.write_bytes(b"fake model, not inference")
        self.server = self.root / "fake-server"
        self.server.write_text(f'''#!{sys.executable}
import argparse, http.server, json, os, pathlib, signal, subprocess, sys, time
root = pathlib.Path({str(self.root)!r})
mode = (root / "mode").read_text()
(root / "server.pid").write_text(str(os.getpid()))
p = argparse.ArgumentParser(); p.add_argument("--port", type=int); p.add_argument("--host", default="127.0.0.1"); args, _ = p.parse_known_args()
if mode == "crash": sys.exit(7)
if mode in ("descendants", "tasks"):
    for i in range(1 if mode == "descendants" else 8):
        subprocess.Popen([sys.executable, "-c", "import os,pathlib,signal,time; os.setsid(); pathlib.Path(" + repr(str(root / ("orphan" + str(i) + ".pid"))) + ").write_text(str(os.getpid())); signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"])
if mode == "memory": payload = bytearray(180 * 1024 * 1024)
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503 if mode == "unready" else 200); self.end_headers()
        self.wfile.write(json.dumps({{"status": "ok"}}).encode())
    def log_message(self, *args): pass
http.server.HTTPServer((args.host, args.port), Handler).serve_forever()
''')
        self.server.chmod(0o700)
        self.mode("normal")

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            try:
                child.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        self.assert_clean()
        self.temp.cleanup()

    def mode(self, name):
        (self.root / "mode").write_text(name)

    def port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def command(self, client="pass", extra=()):
        return [sys.executable, "-B", str(SCRIPT), "--binary", str(self.server),
                "--model", str(self.model), "--backend", "process", "--gpu", "none",
                "--memory-gib", "0.5", "--reserve-gib", "0.001", "--cpus", "4",
                "--wall-seconds", "40", "--startup-seconds", "30", "--port", str(self.port()),
                "--server-log", str(self.root / "server.log"), *extra,
                "--", sys.executable, "-c", client]

    def launch(self, client="pass", extra=()):
        env = dict(os.environ, XDG_RUNTIME_DIR=str(self.root))
        p = subprocess.Popen(self.command(client, extra), env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(p)
        return p

    def finish(self, p, code):
        stdout, stderr = p.communicate(timeout=48)
        self.assertEqual(p.returncode, code, stdout + stderr)
        self.assert_clean()
        return stdout, stderr

    def wait_file(self, name):
        deadline = time.monotonic() + 5
        while not (self.root / name).exists():
            if time.monotonic() > deadline:
                self.fail("Child did not become ready: " + name)
            time.sleep(0.03)

    def assert_clean(self):
        deadline = time.monotonic() + 5
        while True:
            live = [p for p in self.root.glob("*.pid") if Path("/proc/" + p.read_text()).exists()]
            if not live:
                return
            if time.monotonic() >= deadline:
                self.fail("Leaked owned children: " + str(live))
            time.sleep(0.05)

    def test_success_exports_endpoint_disables_autostart_and_cleans(self):
        client = "import os,urllib.request; assert os.environ['LEANSTRAL_BASE_URL'].endswith('/v1'); assert os.environ['IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART']=='0'; print('client ran')"
        out, _ = self.finish(self.launch(client), 0)
        self.assertIn("client ran", out)

    def test_explicit_chat_template_is_forwarded_by_preflight(self):
        template = self.root / "chat template.jinja"
        template.write_text("{{ bos_token }}[INST]{{ messages[0].content }}[/INST]")
        out, _ = self.finish(self.launch(extra=("--preflight-only", "--chat-template-file", str(template))), 0)
        configuration = json.loads(out)
        self.assertEqual(configuration["chat_template_file"], str(template))
        self.assertEqual(configuration["server_argv"][-3:], ["--jinja", "--chat-template-file", str(template)])
        self.assertFalse((self.root / "server.pid").exists())

    def test_missing_chat_template_rejected_before_model_start(self):
        _, err = self.finish(self.launch(extra=("--chat-template-file", str(self.root / "missing.jinja"))), 125)
        self.assertIn("Chat template is absent", err)
        self.assertFalse((self.root / "server.pid").exists())

    def test_client_failure_preserved_and_detached_descendant_killed(self):
        self.mode("descendants")
        client = f"""import os,pathlib,signal,sys,time
pid=os.fork()
if pid:
    time.sleep(.5)
    sys.exit(17)
os.setsid()
pathlib.Path({str(self.root / 'client-orphan.pid')!r}).write_text(str(os.getpid()))
signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(60)
"""
        self.finish(self.launch(client), 17)
        self.assertTrue((self.root / "orphan0.pid").exists())
        self.assertTrue((self.root / "client-orphan.pid").exists())
        receipt = json.loads((self.root / "server.cleanup.json").read_text())
        self.assertTrue(receipt["empty_after"])
        self.assertTrue(receipt["child_termination_proven"])
        self.assertGreaterEqual(len(receipt["descendants_seen"]), 2)

    def test_startup_deadline(self):
        self.mode("unready")
        self.finish(self.launch(extra=("--startup-seconds", "0.4")), 124)

    def test_client_deadline(self):
        self.finish(self.launch("import time; time.sleep(60)", ("--wall-seconds", "0.7")), 124)

    def test_server_crash(self):
        self.mode("crash")
        self.finish(self.launch(), 125)

    def test_sigint_cleans_detached_server_and_client_descendants(self):
        self.mode("descendants")
        client = f"import os,pathlib,time; pathlib.Path({str(self.root / 'client.pid')!r}).write_text(str(os.getpid())); time.sleep(60)"
        p = self.launch(client)
        self.wait_file("client.pid")
        p.send_signal(signal.SIGINT)
        self.finish(p, 130)

    def test_killed_outer_wrapper_still_cleans(self):
        self.mode("descendants")
        p = self.launch("import time; time.sleep(60)")
        self.wait_file("orphan0.pid")
        p.kill()
        self.finish(p, -signal.SIGKILL)

    def test_second_job_rejected_even_on_different_port(self):
        p = self.launch("import time; time.sleep(60)")
        self.wait_file("server.pid")
        second = self.launch()
        out, err = second.communicate(timeout=4)
        self.assertEqual(second.returncode, 125, out + err)
        self.assertIn("owns the selected", err)
        p.terminate()
        self.finish(p, 143)

    def test_port_conflict_never_starts_server(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); sock.listen()
            self.finish(self.launch(extra=("--port", str(sock.getsockname()[1]))), 125)
        self.assertFalse((self.root / "server.pid").exists())

    def test_aggregate_memory_limit(self):
        self.mode("memory")
        self.finish(self.launch("import time; time.sleep(60)", ("--memory-gib", "0.12")), 125)

    def test_aggregate_task_limit(self):
        self.mode("tasks")
        self.finish(self.launch("import time; time.sleep(60)", ("--tasks", "4")), 125)

    def test_preflight_only_does_not_launch(self):
        out, _ = self.finish(self.launch(extra=("--preflight-only",)), 0)
        self.assertEqual(json.loads(out)["event"], "preflight_ok")
        self.assertFalse((self.root / "server.pid").exists())

    def test_cli_defaults_are_10000_wall_and_360_startup(self):
        help_text = subprocess.check_output(
            [sys.executable, "-B", str(SCRIPT), "--help"], text=True)
        self.assertIn("default: 10000", help_text)
        self.assertIn("default: 360", help_text)
        self.assertNotRegex(help_text, r"default: 900\b")
        self.assertNotRegex(help_text, r"default: 1800\b")

    def test_loopback_tcp_hex_and_bind_resolution(self):
        self.assertEqual(runner.ipv4_proc_hex("127.0.0.1"), "0100007F")
        self.assertEqual(runner.resolve_bind("127.0.0.1"), "127.0.0.1")
        with self.assertRaises(runner.RunnerError):
            runner.resolve_bind("0.0.0.0")
        with self.assertRaises(runner.RunnerError):
            runner.resolve_bind("localhost")

    def test_preflight_default_bind_is_loopback(self):
        configuration = json.loads(self.finish(self.launch(extra=("--preflight-only",)), 0)[0])
        self.assertEqual(configuration["bind"], "127.0.0.1")
        self.assertIn("--host", configuration["server_argv"])
        self.assertEqual(configuration["server_argv"][configuration["server_argv"].index("--host") + 1], "127.0.0.1")

    def test_wildcard_bind_is_rejected_before_launch(self):
        _, err = self.finish(self.launch(extra=("--bind", "0.0.0.0")), 2)
        self.assertIn("wildcard", err.lower())
        self.assertFalse((self.root / "server.pid").exists())

    def test_docker0_bind_is_exported_to_client_and_not_loopback(self):
        gateway = runner.iface_ipv4("docker0")
        if not gateway:
            self.skipTest("docker0 IPv4 is unavailable")
        client = (
            "import os,urllib.request; url=os.environ['LEANSTRAL_BASE_URL']; "
            f"assert url.startswith('http://{gateway}:'); "
            "assert os.environ['IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART']=='0'; "
            "print('docker0 client ran')"
        )
        out, _ = self.finish(self.launch(client, extra=("--bind", "docker0")), 0)
        self.assertIn("docker0 client ran", out)

    def test_systemd_properties_have_lifetime_and_aggregate_limits(self):
        command = runner.systemd_prefix("test", {"wall_seconds": 12, "memory_bytes": 12345, "cpus": 2, "tasks": 32})
        for flag in ("--collect", "--property=KillMode=control-group", "--property=RuntimeMaxSec=12",
                     "--property=MemoryMax=12345", "--property=MemorySwapMax=0",
                     "--property=CPUQuota=200%", "--property=TasksMax=32"):
            self.assertIn(flag, command)
        self.assertFalse(any("enable" in value or "unmask" in value for value in command))

    def test_transient_systemd_enforces_real_cgroup_limits_and_cleans(self):
        limits = {"wall_seconds": 10, "memory_bytes": 512 * 1024**2, "cpus": 2, "tasks": 128}
        if not runner.systemd_available(limits):
            self.skipTest("Transient user systemd/cgroup limits unavailable")
        self.mode("descendants")
        client = "from pathlib import Path; c=Path('/proc/self/cgroup').read_text().strip().split('::')[1]; p=Path('/sys/fs/cgroup')/c.lstrip('/'); assert (p/'memory.max').read_text().strip()=='536870912'; assert (p/'memory.swap.max').read_text().strip()=='0'; assert (p/'pids.max').read_text().strip()=='128'; quota,period=map(int,(p/'cpu.max').read_text().split()); assert quota/period==2; print('verified actual cgroup limits')"
        p = subprocess.Popen(self.command(client, ("--backend", "systemd", "--cpus", "2")),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.children.append(p)
        out, _ = self.finish(p, 0)
        self.assertIn("verified actual cgroup limits", out)


if __name__ == "__main__":
    unittest.main()
