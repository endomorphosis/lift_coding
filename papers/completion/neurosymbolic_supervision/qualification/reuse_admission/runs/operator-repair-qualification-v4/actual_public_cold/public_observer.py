import json,os,time,resource,sys,hashlib
from pathlib import Path
nodes=[];reports=[];errors=[]
def pytest_collection_modifyitems(session,config,items):nodes.extend(item.nodeid for item in items)
def pytest_collectreport(report):
 if report.failed:errors.append(str(report.nodeid))
def pytest_runtest_logreport(report):reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'duration':report.duration})
def pytest_sessionfinish(session,exitstatus):
 r=resource.getrusage(resource.RUSAGE_SELF)
 Path(os.environ['NS027_PUBLIC_OBSERVATION']).write_text(json.dumps({'collected':nodes,'reports':reports,'collection_errors':errors,'exitstatus':int(exitstatus),'cpu_seconds':r.ru_utime+r.ru_stime,'maxrss_kib':r.ru_maxrss,'xmltodict_origin':sys.modules['xmltodict'].__file__,'xmltodict_sha256':hashlib.sha256(Path(sys.modules['xmltodict'].__file__).read_bytes()).hexdigest()}))
