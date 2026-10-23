"""Apply the reviewed VDG phase graph under the stopped lane's own fence."""
import fcntl,json,re,time
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.rescue.gate_recovery import admit_gate_repair_task
from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields
root=Path('/home/barberb/lift_coding');w=root/'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog';board=root/'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'
common=['swissknife/scripts/run-vdg-family.mjs','swissknife/scripts/check-vdg-capture.cjs','swissknife/scripts/vdg-evidence.cjs','swissknife/scripts/vdg-connector-artifacts.cjs','swissknife/scripts/vdg-capture-fingerprint.cjs','swissknife/test/e2e/helpers/live-click-session.ts','swissknife/test/e2e/helpers/vdg-family-capture.ts','swissknife/web/js/live-tool-gateway.js','swissknife/src/services/apps/all-app-executable-backend-contract.ts','swissknife/src/services/apps/virtual-desktop-app-manifest.ts','swissknife/src/services/mcp/all-tools-disposition-catalog.ts','swissknife/build-tools/configs/vite.web.config.ts','swissknife/web/js/main-simple.js']
backend=['swissknife/scripts/verify-vdg-backends.mjs','swissknife/scripts/ipfs-kit-kubo-tools.cjs','swissknife/scripts/ipfs-kit-governed-tools.cjs','swissknife/src/services/ipfs/mcp-ipfs-kit-governed-tools-manifest.json','swissknife/src/services/ipfs/mcp-ipfs-kit-descriptor-pack.ts','swissknife/scripts/start-ipfs-kit-mcp-compat.cjs','swissknife/scripts/start-ipfs-datasets-mcp-compat.cjs','swissknife/scripts/all-tools-evidence-lib.cjs','swissknife/scripts/mcpplusplus-profile-e-http.cjs','swissknife/scripts/ipfs_mcp_libp2p_bridge.py','external/ipfs_datasets/ipfs_datasets_py/core_operations/dataset_loader.py','external/ipfs_datasets/ipfs_datasets_py/mcp_server/tools/ipfs_tools/get_from_ipfs.py']
families={'031':('storage',['file-manager','ipfs-explorer','image-viewer','media-player','cinema','peertube']),'032':('datasets',['ai-chat','datasets-browser','model-browser','notes','vibecode']),'033':('accelerate',['device-manager','huggingface','training-manager','accelerate-panel','neural-network-designer','neural-photoshop']),'034':('network',['p2p-network','p2p-chat','p2p-chat-unified','friends-list','navi']),'035':('control',['mcp-control','mcp-plus-plus-explorer','idl-explorer','agent-supervisor','system-monitor','github','api-keys','orb-auto-ui']),'036':('local',['calculator','clock','terminal','glasses-preview','settings','todo','calendar','cron','task-manager','music-studio','music-studio-unified','strudel','strudel-ai-daw','oauth-login','openrouter'])}
notes=[]
def change(text,task,updates):
 lines=text.splitlines(keepends=True);active=False;seen=set();out=[]
 for line in lines:
  if line.startswith('## '):
   if active:
    for key,value in updates.items():
     if key not in seen:out.append(f'- {key}: {value}\n')
   active=line[3:].strip().split(' ',1)[0]==task
  if active:
   match=re.match(r'- ([^:]+):',line)
   if match and match[1] in updates:
    out.append(f'- {match[1]}: {updates[match[1]]}\n');seen.add(match[1]);continue
  out.append(line)
 if active:
  for key,value in updates.items():
   if key not in seen:out.append(f'- {key}: {value}\n')
 return ''.join(out)
def add(text,task,command,validation,files,acceptance,deps=(),browser=False):
 result=admit_gate_repair_task(text,repo_root=root,task_id='VDG-060',repair_task_id=task,command=command,validation=validation,predicted_files=list(dict.fromkeys(files)),acceptance=acceptance,depends_on=list(deps),resource_class='cpu-browser' if browser else 'cpu-small',implementation_timeout_seconds=7200 if browser else 1800)
 text=result.pop('todo_text');notes.append(result);return text
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence,fcntl.LOCK_EX|fcntl.LOCK_NB)
 original=board.read_text();before=dict(parse_todo_task_fields(original,task_header_prefix='## VDG-'))
 assert before['VDG-032-R03']['status']=='pending'
 snap=w/'completion-board-before.todo.snapshot'
 if not snap.exists():snap.write_text(original)
 text=change(original,'VDG-032-R03',{'Deterministic command':'node --test swissknife/test/scripts/vdg-dataset-native-apps.test.mjs','Validation':'node --test swissknife/test/scripts/vdg-dataset-native-apps.test.mjs','Acceptance':'Verify the repaired native dataset controls and exact request/confirmation behavior through executable DOM regressions. Actual GUI capture and full-family acceptance remain mandatory in VDG-032-R01, VDG-032-R02 and VDG-032-R04; this source repair grants no family GO.','Notes':'Original mixed implementation/capture contract is preserved in watchdog/completion-board-before.todo.snapshot. Split into explicit implementation, acquisition and strict acceptance phases to remove the HTTP/libp2p dependency deadlock.'})
 text=add(text,'VDG-013-R01','node --import tsx swissknife/scripts/verify-vdg-backends.mjs','node --import tsx swissknife/scripts/verify-vdg-backends.mjs',backend,'Prove actual owner HTTP and libp2p invocation with verified Profile C identity and exact descriptor CID. Read real workspace bytes, validate a write preview and prove the file stayed unchanged. Backend readiness never substitutes for originating GUI evidence.',deps=['VDG-040-R02'])
 sharedtests=['swissknife/scripts/build-vdg-inputs.test.cjs','swissknife/scripts/check-vdg-capture.test.cjs','swissknife/scripts/run-vdg-all-families.test.mjs','swissknife/scripts/verify-vdg-family.test.mjs','swissknife/scripts/live-tool-gateway-confirmation.test.cjs']
 text=add(text,'VDG-013-R02','node --test '+' '.join(sharedtests),'node --test '+' '.join(sharedtests),common+sharedtests,'Verify fresh inventory, acquisition/acceptance separation, bounded parallel execution, source-bound proof integrity and actual confirmation behavior. Preserve all missing or failed execution evidence as NO_GO.',deps=['VDG-040-R02'])
 text=add(text,'VDG-012-R02','node swissknife/scripts/refresh-vdg-inventory.mjs','node swissknife/scripts/refresh-vdg-inventory.mjs --check',common+['swissknife/scripts/refresh-vdg-inventory.mjs','swissknife/scripts/run-rendered-census.mjs','swissknife/scripts/build-vdg-inputs.cjs','swissknife/scripts/prepare-vdg-rendered-inputs.cjs','swissknife/test-results/virtual-desktop-ipfs-mcp-orb/control-census.json','swissknife/test-results/virtual-desktop-ipfs-mcp-orb/control-tool-matrix.json','swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-app-live-binding-gap-ledger.json'],'Launch every current app and alias, inventory actual rendered controls without clicking tools, and join native exact-tool metadata to current reviewed source contracts and live owner discovery. Preserve all obligations and archive historical ledger inputs.',deps=['VDG-032-R03','VDG-013-R01','VDG-013-R02'],browser=True)
 text=add(text,'VDG-039-R01','node swissknife/scripts/run-vdg-all-families.mjs','node swissknife/scripts/run-vdg-all-families.mjs --check',common+backend+['swissknife/scripts/run-vdg-all-families.mjs'],'Acquire all twelve current source-bound family/transport captures using at most three different families concurrently and sequential transports within a family. Acquisition completion grants no family GO.',deps=['VDG-012-R02','VDG-013-R01'],browser=True)
 gates=[]
 for number,(family,apps) in families.items():
  code='vdg-'+family
  sources=common+backend+[f'swissknife/web/js/apps/{app}.js' for app in apps if (root/f'swissknife/web/js/apps/{app}.js').exists()]
  cells=[]
  for index,transport in enumerate(['http','libp2p'],1):
   task=f'VDG-{number}-R0{index}';cells.append(task)
   updates={'Depends on':'VDG-039-R01','Deterministic command':f'node swissknife/scripts/run-vdg-family.mjs {code} {transport} --capture-only','Validation':f'node swissknife/scripts/check-vdg-capture.cjs {code} {transport}','Acceptance':f'Acquire a complete actual {family} {transport} capture tied to current source and every declared control, with exact report hash and no fatal runner failure. Missing behavior remains NO_GO and is adjudicated by the strict family acceptance task; this row records acquisition only.'}
   if task in before:
    assert before[task]['status']=='pending';text=change(text,task,updates)
   else:
    text=add(text,task,updates['Deterministic command'],updates['Validation'],sources,updates['Acceptance'],deps=['VDG-039-R01'],browser=True)
  gate=f'VDG-{number}-R04' if number=='032' else f'VDG-{number}-R03';gates.append(gate)
  text=add(text,gate,f'node swissknife/scripts/verify-vdg-family.mjs {code}',f'node swissknife/scripts/verify-vdg-family.mjs {code} --check',sources+['swissknife/scripts/verify-vdg-family.mjs',f'swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vdg/families/{family}.json'],f'Full {family} acceptance requires every current control and app-visible tool on every declared transport, real native origins, exact independently verified receipts and event CIDs, actual owner outcomes, confirmation ordering, governed negatives and external-provider outcomes. Never weaken these rules or infer acceptance from acquisition. Refresh stale captures once after a real source repair.',deps=cells,browser=True)
 text=add(text,'VDG-040-R03','node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go','node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go',common+['swissknife/scripts/build-gui-mcp-coverage.cjs','swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json'],'Recompute all six full family acceptance decisions from current independent evidence. GO requires every obligation and no gaps; partial family success and screenshots never suffice.',deps=gates)
 text=change(text,'VDG-060',{'Validation':'node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go'})
 after=dict(parse_todo_task_fields(text,task_header_prefix='## VDG-'))
 assert all(after[k]['status']==v['status'] for k,v in before.items()),'Statuses must remain untouched'
 # Every dependency is declared and the resulting graph must be acyclic.
 seen=set();active=set()
 def visit(task):
  assert task in after,task
  if task in active:raise AssertionError('cycle: '+task)
  if task in seen:return
  active.add(task)
  for dep in after[task].get('depends_on','').split(','):
   if dep.strip():visit(dep.strip())
  active.remove(task);seen.add(task)
 for task in after:visit(task)
 temp=board.with_suffix('.todo.completion.tmp');temp.write_text(text);temp.replace(board)
 (w/'completion-board-plan-receipt.json').write_text(json.dumps({'observed_at':time.time(),'task_count_before':len(before),'task_count_after':len(after),'statuses_preserved':True,'rewritten_pending_contracts':['VDG-032-R03','VDG-032-R01','VDG-032-R02','VDG-060'],'admitted':notes,'full_acceptance_tasks':gates,'completion_gate':'VDG-040-R03 -> VDG-060','work_complete':False,'completion_authority':False},indent=2)+'\n')
 print(json.dumps({'tasks_before':len(before),'tasks_after':len(after),'statuses_preserved':True,'admitted':len(notes),'acceptance_gates':gates}))
