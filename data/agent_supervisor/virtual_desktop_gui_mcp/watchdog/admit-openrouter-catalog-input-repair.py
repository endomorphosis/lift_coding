"""Fenced R23 admission for source-bound public catalog inputs; default is read-only."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import time
from ipfs_accelerate_py.agent_supervisor.rescue.gate_recovery import admit_gate_repair_task
from ipfs_accelerate_py.agent_supervisor.rescue.storage_pressure import check_storage_capacity
from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields
ROOT=Path(__file__).resolve().parents[4]
WATCHDOG=Path(__file__).resolve().parent
BOARD=ROOT/'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'
TARGET='VDG-039-R01'
REPAIR='VDG-013-R23'
DEPENDENCIES=['VDG-013-R22']
WRAPPER='node swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs -- '
VALIDATION='python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-catalog-input-repair.py'
COMMAND=VALIDATION
ORIGINAL_COMMANDS={
 'VDG-039-R01':('node swissknife/scripts/run-vdg-all-families.mjs --timeout-seconds 22200','node swissknife/scripts/run-vdg-all-families.mjs --check'),
 'VDG-036-R01':('node swissknife/scripts/run-vdg-family.mjs vdg-local http --capture-only','node swissknife/scripts/check-vdg-capture.cjs vdg-local http'),
 'VDG-036-R02':('node swissknife/scripts/run-vdg-family.mjs vdg-local libp2p --capture-only','node swissknife/scripts/check-vdg-capture.cjs vdg-local libp2p'),
 'VDG-036-R03':('node swissknife/scripts/verify-vdg-family.mjs vdg-local --timeout-seconds 22200','node swissknife/scripts/verify-vdg-family.mjs vdg-local --check'),
 'VDG-040-R03':('node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go','node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go'),
 'VDG-060':('python3 swissknife/scripts/vdg_closeout_requires_go.py','node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go'),
}
OWN_SOURCES=[
 'swissknife/web/js/apps/openrouter.js',
 'swissknife/test/e2e/families/local-negative-mcp.spec.ts',
 'swissknife/scripts/build-family-mcp-spec.cjs',
 'swissknife/scripts/vdg-openrouter-catalog-input.cjs',
 'swissknife/scripts/capture-openrouter-catalog-input.mjs',
 'swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs',
 'swissknife/scripts/vdg-openrouter-catalog-input.test.mjs',
 'swissknife/test/scripts/vdg-openrouter-catalog-snapshot.test.mjs',
 'swissknife/test/e2e/smoke/vdg-openrouter-catalog-snapshot-smoke.mjs',
 'swissknife/web/public/vdg-public-inputs/openrouter/65a3034c116179fac2ba1511796f0e1a014955986295385dfac8fbc35b7271bc.json',
 'swissknife/web/public/vdg-public-inputs/openrouter/provenance-19726a9dac6901f79566e387871e286f32633b415ef28fb5f0912e94aa125e3c.json',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-catalog-input-repair.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/admit-openrouter-catalog-input-repair.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/test-openrouter-catalog-input-admission.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/test-openrouter-catalog-input-ops.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-case-cost-diagnostic.py',
]
ACCEPTANCE=(
 'Bind actual public OpenRouter response bytes, HTTPS200 provenance, retrieval time and full unique model-ID set '
 'consistently across live DOM census, both Local profiles, resumes and cached validation. Preserve every raw model, '
 'source-pin immutable raw/provenance SHA values in the app, verify hashes before JSON interpretation, isolate permanent '
 'snapshot cache from ordinary live TTL cache, and fail closed on mismatch without live fallback or omitted controls. '
 'Require meaningful fresh app/guard/Todo/parity tests plus actual canonical registered-factory Chrome proof in both profiles '
 'with all468 real models and1881 controls, trusted real actions on the new declared MiniMax ID, honest metadata, original '
 'Default persistence, no provider POST/external catalog GET/pageerrors, no module overrides and exact owned cleanup. '
 'Archive original HTTP2073 clean rows/4124 verified PNGs and actual6h deadline, original libp2p388 rows/764 verified PNGs '
 'with four not-visible MiniMax-free controls83–86; never relabel them accepted or claim an unretained historical raw rename. '
 'Preserve ten nonLocal acquisition fingerprints/run IDs/report hashes/1714 rows via a genuine new Local input and real census. '
 'Strengthen exactly six still-pending task producer/validation pairs with an input-check wrapper before the exact original '
 'argv, including reuse/strict/aggregate/060. Preserve all other task fields/status/history/attempt/refusal budgets and '
 'existing timeout bounds. Ordinary hard-deadline checkpoint retry remains required; snapshot binding is no timeout waiver. '
 'Original039 must acquire both new complete Local profiles, all12 current cells, then six strict GO gates, aggregate GO '
 'and060 before any program GO. No optional OpenRouter storage isolation, fake provider jobs or manual task completion.'
)
def require(condition,message):
 if not condition:raise ValueError(message)
def tasks(text):return dict(parse_todo_task_fields(text,task_header_prefix='## VDG-'))
def graph(after):
 active,seen=set(),set()
 def visit(task):
  require(task in after and task not in active,'Missing dependency or cycle: '+task)
  if task in seen:return
  active.add(task)
  for dep in after[task].get('depends_on','').split(','):
   if dep.strip():visit(dep.strip())
  active.remove(task);seen.add(task)
 for task in after:visit(task)
def replace_field(text,task,key,expected,replacement):
 pattern=re.compile(r'(^## '+re.escape(task)+r'\b[^\n]*\n)(.*?)(?=^## |\Z)',re.M|re.S)
 matches=list(pattern.finditer(text));require(len(matches)==1,'Expected one task block: '+task);match=matches[0]
 label={'deterministic_command':'Deterministic command','validation':'Validation'}[key]
 field=re.compile(r'^(- '+re.escape(label)+r': )([^\n]*)$',re.M)
 values=list(field.finditer(match.group(2)));require(len(values)==1 and values[0].group(2)==expected,'Exact original field changed: '+task+'/'+key)
 body=field.sub(lambda m:m.group(1)+replacement,match.group(2),count=1)
 return text[:match.start()]+match.group(1)+body+text[match.end():]
def build_admission(original,*,root=ROOT):
 before=tasks(original)
 require(all(task in before for task in ORIGINAL_COMMANDS),'Required pending pipeline task missing')
 if REPAIR in before:
  own=before[REPAIR];require(own.get('deterministic_command')==COMMAND and own.get('validation')==VALIDATION and own.get('depends_on')==', '.join(DEPENDENCIES),'Existing R23 contract differs')
  require(REPAIR in [v.strip() for v in before[TARGET].get('depends_on','').split(',')],'Original batch lacks R23 dependency')
  for task,pair in ORIGINAL_COMMANDS.items():
   for key,command in zip(('deterministic_command','validation'),pair):require(before[task].get(key)==WRAPPER+command,'Existing guarded command differs: '+task)
  graph(before)
  return {'todo_text':original,'admitted':False,'reason':'already_admitted','derived_task_id':REPAIR,'work_complete':False,'completion_authority':False},before,before
 require(all(before[task].get('status')=='pending' for task in ORIGINAL_COMMANDS),'All six strengthened pipeline tasks must still be pending')
 require(all(before.get(task,{}).get('status')=='completed' for task in DEPENDENCIES),'R22 must naturally complete before R23')
 for task,pair in ORIGINAL_COMMANDS.items():
  for key,command in zip(('deterministic_command','validation'),pair):require(before[task].get(key)==command,'Original command changed: '+task+'/'+key)
 predicted=[v.strip() for v in before[TARGET].get('predicted_files','').split(',') if v.strip()]
 result=admit_gate_repair_task(original,repo_root=root,task_id=TARGET,repair_task_id=REPAIR,command=COMMAND,validation=VALIDATION,predicted_files=list(dict.fromkeys([*predicted,*OWN_SOURCES])),acceptance=ACCEPTANCE,depends_on=DEPENDENCIES,resource_class='cpu-small',implementation_timeout_seconds=1800)
 amended=result['todo_text']
 for task,pair in ORIGINAL_COMMANDS.items():
  for key,command in zip(('deterministic_command','validation'),pair):amended=replace_field(amended,task,key,command,WRAPPER+command)
 after=tasks(amended);require(set(after)==set(before)|{REPAIR},'Unexpected task creation/removal')
 for task,fields in before.items():
  expected=dict(fields)
  if task==TARGET:expected['depends_on']=', '.join(dict.fromkeys([*(v.strip() for v in fields.get('depends_on','').split(',') if v.strip()),REPAIR]))
  if task in ORIGINAL_COMMANDS:
   for key,command in zip(('deterministic_command','validation'),ORIGINAL_COMMANDS[task]):expected[key]=WRAPPER+command
  require(after[task]==expected,'Unapproved existing task/history change: '+task)
 require(after[REPAIR].get('status')=='pending' and after[REPAIR].get('implementation_timeout_seconds')=='1800' and after[REPAIR].get('resource_class')=='cpu-small','Wrong focused repair bounds')
 graph(after);result['todo_text']=amended;return result,before,after

def verify_owned_holds(watchdog=WATCHDOG):
 receipt=json.loads((watchdog/'r23-catalog-drift-repair-hold.json').read_text())
 require(receipt.get('token')=='08af974871cc4577a9744d6043df8c80' and receipt.get('lane_pid')==1960744,'Reviewed owned R23 stop identity changed')
 for name,pin in receipt['markers'].items():
  require(name in ('HOLD','repair-dispatcher.hold'),'Unexpected hold marker')
  path=watchdog/name;info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_dev==pin['device'] and info.st_ino==pin['inode'],'Owned hold inode/UID changed')
  require(hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256'],'Owned hold bytes changed');value=json.loads(path.read_text())
  require(value.get('token')==receipt['token'] and value.get('lane_pid')==receipt['lane_pid'],'Owned hold token/owner changed')
 require(set(receipt['markers'])=={'HOLD','repair-dispatcher.hold'},'Both reviewed owned markers required')

def node_scripts(argv):
    """Possible entrypoints, conservatively branching on unknown option arity.

    Script arguments are never searched. Known value options consume their
    operand, so a title or warning destination cannot masquerade as a script.
    Unknown options may be boolean or consume one value: either interpretation
    must exclude an active capture before admission can change its sources.
    """
    if not argv or Path(argv[0]).name not in {"node", "nodejs"}:
        return set()
    value_options = {"--import", "--require", "-r", "--loader", "--experimental-loader",
                     "--conditions", "-C", "--title", "--redirect-warnings", "--env-file",
                     "--env-file-if-exists", "--inspect-port", "--diagnostic-dir",
                     "--report-directory", "--report-filename", "--icu-data-dir",
                     "--openssl-config", "--experimental-policy", "--policy-integrity",
                     "--snapshot-blob", "--heap-prof-dir", "--heap-prof-name",
                     "--cpu-prof-dir", "--cpu-prof-name", "--input-type"}
    boolean_options = {"--no-warnings", "--trace-warnings", "--enable-source-maps",
                       "--test", "--test-only", "--trace-uncaught", "--no-deprecation",
                       "--trace-deprecation", "--throw-deprecation", "--use-strict",
                       "--experimental-default-config-file", "--preserve-symlinks",
                       "--preserve-symlinks-main", "--no-experimental-repl-await"}
    pending, visited, scripts = [1], set(), set()
    while pending:
        index = pending.pop()
        if index in visited or index >= len(argv):
            continue
        visited.add(index)
        value = argv[index]
        if value == "--":
            if index + 1 < len(argv):
                scripts.add(argv[index + 1])
            continue
        if value in {"-e", "--eval", "-p", "--print", "--run"} or value.startswith(("--eval=", "--print=", "--run=", "-e", "-p")):
            continue
        if value in value_options:
            pending.append(index + 2)
        elif value in boolean_options or value.startswith("-") and "=" in value:
            pending.append(index + 1)
        elif value.startswith("-"):
            pending.extend((index + 1, index + 2))
        else:
            scripts.add(value)
    return scripts


def node_script(argv):
    scripts = node_scripts(argv)
    return next(iter(scripts)) if len(scripts) == 1 else None


def active_captures(root=ROOT, proc_root=Path("/proc")):
    """Inspect actual Node script operands, never arbitrary argument data."""
    paths = {root / "swissknife/scripts" / name for name in
             ("run-vdg-family.mjs", "run-vdg-all-families.mjs", "verify-vdg-family.mjs", "run-with-vdg-openrouter-catalog-input.mjs")}
    found = []
    for directory in proc_root.iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            if directory.stat().st_uid != os.getuid():
                continue
            argv = (directory / "cmdline").read_bytes().decode().rstrip("\0").split("\0")
            for script in node_scripts(argv):
                candidate = Path(script)
                if not candidate.is_absolute():
                    candidate = (directory / "cwd").resolve(strict=True) / candidate
                if candidate.resolve() in paths:
                    if (directory / "exe").resolve(strict=True).name in {"node", "nodejs"}:
                        found.append(int(directory.name))
                    break
        except (OSError, UnicodeError):
            # A disappearing process cannot own a surviving lifecycle lock.
            if directory.exists():
                raise
    return found


@contextmanager
def lifecycle_fence(watchdog=WATCHDOG, root=ROOT):
    lane = watchdog / "lanes/vdg-planning"
    descriptor = os.open(lane / "vdg-planning.resume.lock", os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), "Unsafe lifecycle lock ownership")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = json.loads((lane / "vdg_planning_status.json").read_text())
        pid = status.get("pid")
        require(type(pid) is int and pid > 0 and not Path(f"/proc/{pid}").exists(), "Exact prior lane must be absent")
        require(int((lane / "vdg_planning_bundle_supervisor.pid").read_text().strip()) == pid,
                "Canonical stopped status and independent owner PID file disagree")
        require(status.get("state") == "stopped" and status.get("terminal_reason") == "resume_stopped", "Canonical owned stop is required")
        hold = json.loads((watchdog / "repair-dispatcher.hold").read_text())
        require(hold.get("reason") == "controlled VDG completion repairs" and hold.get("lane_pid") == pid,
                "An explicit controlled repair hold must bind the stopped owner")
        require(not active_captures(root), "An actual owned capture entrypoint remains active")
        verify_owned_holds(watchdog)
        yield {"lane_pid": pid, "lock_inode": info.st_ino, "lock_device": info.st_dev,
               "hold_sha256": hashlib.sha256((watchdog / "repair-dispatcher.hold").read_bytes()).hexdigest()}
    finally:
        os.close(descriptor)


def recheck_fence(identity, watchdog=WATCHDOG, root=ROOT):
    lane = watchdog / "lanes/vdg-planning"
    lock = (lane / "vdg-planning.resume.lock").lstat()
    require(stat.S_ISREG(lock.st_mode) and lock.st_uid == os.getuid()
            and lock.st_ino == identity["lock_inode"] and lock.st_dev == identity["lock_device"], "Lifecycle fence path changed")
    status = json.loads((lane / "vdg_planning_status.json").read_text())
    require(status.get("pid") == identity["lane_pid"] and status.get("state") == "stopped"
            and status.get("terminal_reason") == "resume_stopped"
            and not Path(f"/proc/{identity['lane_pid']}").exists(), "Stopped owner changed during preflight")
    require(hashlib.sha256((watchdog / "repair-dispatcher.hold").read_bytes()).hexdigest() == identity["hold_sha256"],
            "Controlled repair hold changed during preflight")
    verify_owned_holds(watchdog)
    require(not active_captures(root), "An owned capture started during admission preflight")


def atomic_write(path, text):
    temporary = path.with_name(f".{path.name}.r23-{os.getpid()}.tmp")
    try:
        with temporary.open("x") as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)



def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args(argv)
 with lifecycle_fence() as identity:
  original=BOARD.read_text();result,before,after=build_admission(original)
  spec=importlib.util.spec_from_file_location('r23_catalog_verifier',WATCHDOG/'verify-openrouter-catalog-input-repair.py');verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
  proof=verifier.verify_ready_proof(require_admission=not result.get('admitted'))
  require(BOARD.read_text()==original,'Taskboard changed during product preflight');recheck_fence(identity)
  amended=result.pop('todo_text')
  if not result.get('admitted'):
   print(json.dumps({'already_admitted':True,'product_preflight':proof,'work_complete':False,'completion_authority':False}));return
  require(len(before)==64 and len(after)==65,'Reviewed64-to65 task transition required')
  transition=verifier.verify_transition(original,amended,expected_repair_fields=after[REPAIR])
  before_path=WATCHDOG/'completion-board-before-catalog-input.todo.snapshot';after_path=WATCHDOG/'completion-board-after-catalog-input.todo.snapshot'
  if args.apply:
   require(check_storage_capacity([BOARD,WATCHDOG])['ok'],'Durable taskboard storage admission failed')
   for path,content in [(before_path,original),(after_path,amended)]:
    if path.exists():require(path.read_text()==content,'Existing immutable board snapshot differs')
    else:atomic_write(path,content)
   recheck_fence(identity);require(BOARD.read_text()==original,'Taskboard changed before guarded write');atomic_write(BOARD,amended)
  receipt={'schema':'swissknife.vdg-openrouter-catalog-admission.v1','observed_at':time.time(),'apply_requested':args.apply,'tasks_before':len(before),'tasks_after':len(after),'board_before_sha256':hashlib.sha256(original.encode()).hexdigest(),'board_after_sha256':hashlib.sha256(amended.encode()).hexdigest(),'before_snapshot':before_path.name,'after_snapshot':after_path.name,'statuses_history_and_bounds_preserved':True,'guarded_command_fields':12,'exact_original_child_argv_preserved':True,'identity':identity,'repair_fields':after[REPAIR],'admission':result,'transition':transition,'canonical_product_preflight':proof,'gui_acceptance':False,'work_complete':False,'completion_authority':False}
  if args.apply:atomic_write(WATCHDOG/'catalog-input-admission.json',json.dumps(receipt,indent=2)+'\n')
  print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__':main()
