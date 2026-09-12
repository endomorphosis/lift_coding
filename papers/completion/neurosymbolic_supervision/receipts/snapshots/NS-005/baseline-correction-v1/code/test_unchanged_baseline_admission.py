import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('admission',HERE/'unchanged_baseline_admission.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
class ActualPytestAdmission(unittest.TestCase):
 def run_case(self,source):
  with tempfile.TemporaryDirectory(prefix='ns-baseline-negative-') as tmp:
   root=Path(tmp);(root/'test_baseline.py').write_text(source);data=[];rc=[]
   for name,extra in [('collect',['--collect-only']),('run',[])]:
    out=root/(name+'.json');env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONPATH':str(HERE),'BASELINE_OBSERVATION':str(out)}
    p=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider','-p','baseline_capture',*extra],cwd=root,env=env,capture_output=True,text=True,timeout=20);rc.append(p.returncode);data.append(json.loads(out.read_text()))
   return data,rc
 def admission(self,source):
  (collection,execution),(crc,rrc)=self.run_case(source)
  return A.qualify(collection,execution,source_before='fixed',source_after='fixed',collect_returncode=crc,run_returncode=rrc)
 def test_real_pass(self):self.assertEqual(self.admission('def test_ok(): assert 2+2==4\n')['executed_passed_count'],1)
 def test_empty_file_is_not_nonempty_suite(self):
  with self.assertRaises(A.BaselineAdmissionError):self.admission('# existing test-file path, no tests\n')
 def test_all_skipped_is_not_qualified(self):
  with self.assertRaises(A.BaselineAdmissionError):self.admission('import pytest\n@pytest.mark.skip(reason="missing optional runtime")\ndef test_optional(): pass\n')
 def test_failing_test_is_not_qualified(self):
  with self.assertRaises(A.BaselineAdmissionError):self.admission('def test_bad(): assert False\n')
 def test_collection_import_error_is_not_qualified(self):
  with self.assertRaises(A.BaselineAdmissionError):self.admission('import absent_ns005_dependency_987\n')
 def test_teardown_failure_is_not_qualified(self):
  with self.assertRaises(A.BaselineAdmissionError):self.admission('import pytest\n@pytest.fixture\ndef resource():\n yield 1\n raise ValueError("teardown")\ndef test_resource(resource): assert resource==1\n')
 def test_mutated_source_is_not_qualified(self):
  (c,e),(cr,rr)=self.run_case('def test_ok(): assert True\n')
  with self.assertRaisesRegex(A.BaselineAdmissionError,'baseline_source_changed'):A.qualify(c,e,source_before='old',source_after='new',collect_returncode=cr,run_returncode=rr)
 def test_missing_execution_report_is_not_qualified(self):
  (c,e),(cr,rr)=self.run_case('def test_ok(): assert True\n');e['reports']=[]
  with self.assertRaisesRegex(A.BaselineAdmissionError,'incomplete'):A.qualify(c,e,source_before='fixed',source_after='fixed',collect_returncode=cr,run_returncode=rr)
if __name__=='__main__':unittest.main(verbosity=2)
