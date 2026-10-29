#!/usr/bin/env python3
"""Pinned SDK code comparison tests; RAM files only, no SDK execution."""
import gc,hashlib,importlib.util,marshal,os,pathlib,tempfile,types,unittest
ROOT=pathlib.Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',str(pathlib.Path(__file__).resolve().parents[1]))).resolve()
GATE=pathlib.Path(os.environ.get('SVF_GATE_CANDIDATE',str(ROOT/'scripts/svf_backends/validate_supervisor_foundation.py')))
spec=importlib.util.spec_from_file_location('gate_code_lifetime',GATE);gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class GateCodeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-code-lifetime-',dir='/dev/shm');self.root=pathlib.Path(self.tmp.name)
  self.path=self.root/'pinned.py';self.path.write_text("class Example:\n def run(self, value=True, *, other=-0.0):\n  literal=(True, 0.0, 'pinned')\n  def nested():\n   return value, literal\n  return nested\n")
  self.namespace={'__name__':'svf_pinned_fixture','__package__':'','__file__':str(self.path)}
  exec(compile(self.path.read_bytes(),str(self.path),'exec',dont_inherit=True),self.namespace)
  self.cls=self.namespace['Example'];self.classes={'Example':self.cls};self.paths={'Example':'pinned.py'};self.methods={'Example':['run']};self.expected={'pinned.py':gate.sha(self.path)}
 def tearDown(self):self.tmp.cleanup()
 def hashes(self):return gate.sdk_observer_code_hashes(self.root,self.classes,self.paths,self.methods,self.expected)
 def altered(self,**changes):
  old=self.cls.run;code=old.__code__.replace(**changes)
  cells=tuple((lambda x:lambda:x)(None).__closure__[0] for _ in code.co_freevars) or None
  new=types.FunctionType(code,old.__globals__,old.__name__,old.__defaults__,cells);new.__module__=old.__module__;new.__kwdefaults__=old.__kwdefaults__;self.cls.run=new
  with self.assertRaisesRegex(ValueError,'SDK (imported method differs|compiler method origin differs)'):self.hashes()
 def test_fixture_source_method(self):self.assertRegex(self.hashes()['Example','run'],'^[a-f0-9]{64}$')
 def test_source_changed(self):
  self.path.write_text(self.path.read_text()+'# changed\n')
  with self.assertRaisesRegex(ValueError,'SDK compiler source differs'):self.hashes()
 def test_wrong_method(self):
  self.methods={'Example':['missing']}
  with self.assertRaisesRegex(ValueError,'SDK compiler method origin differs'):self.hashes()
 def test_foreign_module(self):
  self.cls.run.__module__='foreign'
  with self.assertRaisesRegex(ValueError,'SDK compiler method origin differs'):self.hashes()
 def test_filename(self):self.altered(co_filename=str(self.root/'foreign.py'))
 def test_name(self):self.altered(co_name='other')
 def test_qualname(self):self.altered(co_qualname='Foreign.run')
 def test_first_line(self):self.altered(co_firstlineno=100)
 def test_flags(self):self.altered(co_flags=self.cls.run.__code__.co_flags ^ 0x40)
 def test_line_table(self):self.altered(co_linetable=b'')
 def test_exception_table(self):self.altered(co_exceptiontable=b'\x00')
 def test_stack_size(self):self.altered(co_stacksize=self.cls.run.__code__.co_stacksize+1)
 def test_varnames(self):
  c=self.cls.run.__code__;self.altered(co_varnames=tuple('different' if x=='other' else x for x in c.co_varnames))
 def test_cellvars(self):
  c=self.cls.run.__code__;self.altered(co_cellvars=tuple('different' if x=='value' else x for x in c.co_cellvars))
 def test_argcount(self):self.altered(co_argcount=1)
 def test_kwonlycount(self):self.altered(co_kwonlyargcount=0)
 def test_names(self):self.altered(co_names=('different',))
 def test_bytecode(self):
  c=self.cls.run.__code__;self.altered(co_code=bytes([9,0])+c.co_code[2:])
 def test_typed_bool_int_constant(self):
  c=self.cls.run.__code__;self.altered(co_consts=tuple(tuple(1 if y is True else y for y in x) if type(x) is tuple else x for x in c.co_consts))
 def test_signed_zero_constant(self):
  c=self.cls.run.__code__;self.altered(co_consts=tuple(tuple(-0.0 if type(y) is float and y==0 else y for y in x) if type(x) is tuple else x for x in c.co_consts))
 def test_nested_code(self):
  c=self.cls.run.__code__;self.altered(co_consts=tuple(x.replace(co_filename='foreign_nested.py') if isinstance(x,types.CodeType) else x for x in c.co_consts))
 def test_freevars(self):
  c=self.cls.run.__code__;self.altered(co_freevars=('foreign',))
 def test_source_compiler_tree_lifetime_matches_observer(self):
  # The tuple used for another method's keyword defaults is shared with run's
  # literal by the compiler, but that extra reference dies after module load.
  self.path.write_text('class Example:\n def other(self, *, value=None, label=None): pass\n def run(self): return ("value","label")\n')
  ns={'__name__':'svf_pinned_fixture','__package__':'','__file__':str(self.path)}
  compiled=compile(self.path.read_bytes(),str(self.path),'exec',dont_inherit=True);exec(compiled,ns)
  self.cls=ns['Example'];self.classes={'Example':self.cls};self.expected={'pinned.py':gate.sha(self.path)}
  observed=hashlib.sha256(marshal.dumps(self.cls.run.__code__)).hexdigest();stable=marshal.dumps(self.cls.run.__code__,0)
  del compiled;gc.collect()
  self.assertEqual(stable,marshal.dumps(self.cls.run.__code__,0))
  self.assertEqual(self.hashes()['Example','run'],observed)

if __name__=='__main__':unittest.main()
