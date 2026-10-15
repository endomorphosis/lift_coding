"""Authored SQL boundary fixtures; no catalog/current-owner authority."""
import json
import shutil
import tempfile
from pathlib import Path
import pytest
from capsule_io import ROOT,sha,wire
from metadata_selection import row,select_task_rows

@pytest.fixture
def fixture():
 import duckdb
 from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as native
 parent=Path(tempfile.mkdtemp(prefix='owned-sql-control-',dir=ROOT));output=parent/'metadata';output.mkdir()
 head={'fixture':'no-current-owner-authority'};snapshot='b'*64
 cx=duckdb.connect(str(output/'metadata.duckdb'),config={'threads':'1','memory_limit':'128MB'})
 cx.execute('CREATE TABLE metadata_rows(family VARCHAR,row_id VARCHAR,row_ordinal BIGINT,payload_sha256 VARCHAR,source_snapshot_sha256 VARCHAR,payload_json VARCHAR)')
 families={'source_files':[],'codec_views':[]}
 for index in range(5):
  path=f'fixture{index}.py'
  families['source_files'].append(row('source',{'path':path,'head':head,'source_text':'pass\n'}))
  for arm in ['minified','aliased']:
   families['codec_views'].append(row('codec',{'path':path,'arm':arm,'codec':{'bindings':{'head':head},
    'expansion_sidecar':{'aliases':{'enabled':arm=='aliased'}}}}))
 for family,values in families.items():
  for ordinal,payload in enumerate(values):
   n=native._row(family,payload,ordinal,snapshot)
   cx.execute('INSERT INTO metadata_rows VALUES (?,?,?,?,?,?)',[family,n['row_id'],ordinal,n['payload_sha256'],snapshot,
    json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)])
 cx.close()
 data={'metadata_output':output,'native_metadata':{'source_snapshot_sha256':snapshot},
  'task':{'sources':[{'path':'fixture0.py'}]},'head':head}
 try:yield data
 finally:shutil.rmtree(parent)

def mutate(fixture,sql,params=None):
 import duckdb
 cx=duckdb.connect(str(fixture['metadata_output']/'metadata.duckdb'),config={'threads':'1','memory_limit':'128MB'})
 try:cx.execute(sql,params or [])
 finally:cx.close()

def test_authored_complete_leaf_scope(fixture):
 sources,codecs=select_task_rows(**fixture)
 assert set(sources)=={'fixture0.py'} and set(codecs['fixture0.py'])=={'minified','aliased'}

def test_oversize_malformed_json_rejected_before_hydration(fixture):
 mutate(fixture,"UPDATE metadata_rows SET payload_json=? WHERE family='source_files' AND row_ordinal=0",['x'*262145])
 with pytest.raises(ValueError,match='before payload hydration'):select_task_rows(**fixture)

def test_native_outer_identity_corruption_rejected(fixture):
 mutate(fixture,"UPDATE metadata_rows SET row_id=? WHERE family='source_files' AND row_ordinal=0",['a'*64])
 with pytest.raises(ValueError,match='native SQL row identity'):select_task_rows(**fixture)

def test_missing_source_scope_rejected(fixture):
 mutate(fixture,"DELETE FROM metadata_rows WHERE family='codec_views' AND row_ordinal=0")
 with pytest.raises(ValueError,match='before payload hydration'):select_task_rows(**fixture)

def test_unexpected_selector_refused(fixture):
 fixture['task']['sources']=[{'path':'not-indexed.py'}]
 with pytest.raises(ValueError,match='unique source'):select_task_rows(**fixture)

def test_wrong_snapshot_refused(fixture):
 fixture['native_metadata']['source_snapshot_sha256']='c'*64
 with pytest.raises(ValueError,match='snapshot binding'):select_task_rows(**fixture)
