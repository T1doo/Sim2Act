"""The original full mutable counter contract, without optional Source ownership.

Every original case is mandatory in a fresh interpreter. No skip, gate patch or
assertion relaxation is used to make immutable Source facts impersonate dicts.
Default native ownership is covered in test_counter_owned_protocol.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def test_original_raw_counter_matrix_without_optional_source(tmp_path):
    root=Path(__file__).resolve().parents[1]
    report=tmp_path/'raw-counter.xml'
    code=r'''
import importlib.abc,sys
class MissingNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='sim2act._cold_source_owned_impl':
   raise ModuleNotFoundError('Synthetic absent optional Source extension',name=fullname)
sys.meta_path.insert(0,MissingNative())
from sim2act import _cold_source_packet as owned
assert owned.available() is False and owned.image.View is None
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
'''
    command=[sys.executable,'-c',code,'tests/counter_loaded_cases.py','-q',
        '-p','no:cacheprovider','--basetemp='+str(tmp_path/'raw-matrix'),
        '--junitxml='+str(report)]
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=120)
    (tmp_path/'raw-counter.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
    cases=list(ET.parse(report).getroot().iter('testcase'))
    assert len(cases)==25
    assert all(c.find('failure') is None and c.find('error') is None
        and c.find('skipped') is None for c in cases)
    (tmp_path/'raw-counter-result.json').write_text(json.dumps(dict(
        status='PASS',cases=25,skips=0,optional_source_extension=False,
        classification='ORIGINAL_MUTABLE_COUNTER_FULL_MATRIX_NOT_DEFAULT_OWNERSHIP'),indent=2)+'\n')
