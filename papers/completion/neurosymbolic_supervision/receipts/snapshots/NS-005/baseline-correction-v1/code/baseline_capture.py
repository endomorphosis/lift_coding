"""Pytest observation plugin. It never selects, edits or repairs tests."""
import json,os,platform,importlib.metadata
from pathlib import Path
_DATA={'schema':'unchanged-pytest-observation/v1','collected':[],'collection_errors':[],'reports':[]}
def pytest_collection_finish(session):
 _DATA['collected']=[item.nodeid for item in session.items]
def pytest_collectreport(report):
 if report.failed:_DATA['collection_errors'].append(report.nodeid)
def pytest_runtest_logreport(report):
 _DATA['reports'].append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome})
def pytest_sessionfinish(session,exitstatus):
 _DATA.update({'exitstatus':int(exitstatus),'python':platform.python_version(),'pytest':importlib.metadata.version('pytest')})
 Path(os.environ['BASELINE_OBSERVATION']).write_text(json.dumps(_DATA,sort_keys=True,indent=2)+'\n')
