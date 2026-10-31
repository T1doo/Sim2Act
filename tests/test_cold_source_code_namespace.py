"""Native code witnesses keep fresh checks and callback boundaries."""
import subprocess
import sys

import pytest


def isolated(body):
    result = subprocess.run([sys.executable, '-c', body], capture_output=True,
                            text=True, timeout=15)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)


@pytest.mark.parametrize('spaces', [1, 64, 70])
def test_repeated_namespaces_remain_fresh_and_bounded(spaces):
    isolated(r'''
import gc
from sim2act import _cold_source_owned_impl as native
def target(value=1):return value
state=(target,target.__code__,target.__defaults__,None,(),None,())
entry=('target',target,(state,))
spaces=[{'target':target} for _ in range(SPACES)]
witnesses=tuple((space,(entry,)) for space in spaces)*2
constants=tuple((space,(('target',target),)) for space in spaces)*2
native.register_code(0,(witnesses,(),constants))
for index in range(1,9):native.register_code(index,((),(),()))
for enabled in (False,True):
 gc.enable() if enabled else gc.disable()
 assert native.verify_code() is True
 assert gc.isenabled() is enabled
 # No namespace/code verdict can survive even one call.
 for space in (spaces[0],spaces[-1]):
  space[17]='foreign key'
  assert native.verify_code() is False
  del space[17]
  assert native.verify_code() is True
 old=target.__defaults__;target.__defaults__=(2,)
 assert native.verify_code() is False
 target.__defaults__=old
 assert native.verify_code() is True
 assert gc.isenabled() is enabled
'''.replace('SPACES', str(spaces)))


def test_namespace_rejection_precedes_foreign_hash_or_equality():
    isolated(r'''
from sim2act import _cold_source_owned_impl as native
events=[]
def target():pass
class Foreign:
 def __hash__(self):events.append('hash');return hash('target')
 def __eq__(self,other):events.append('equal');return True
foreign=Foreign();space={foreign:target};events.clear()
state=(target,target.__code__,None,None,(),None,())
entry=('target',target,(state,))
native.register_code(0,(((space,(entry,)),),(),()))
for index in range(1,9):native.register_code(index,((),(),()))
assert native.verify_code() is False
assert events==[]
''')


def test_class_lookup_callback_cannot_carry_namespace_check_to_next_family():
    isolated(r'''
from sim2act import _cold_source_owned_impl as native
events=[];active=False
def target():pass
space={'target':target}
class Foreign:
 def __hash__(self):return hash('probe')
 def __eq__(self,other):
  global active
  if active:
   events.append('class lookup');space[17]='changed after module checks';active=False
  return other=='probe'
foreign=Foreign();kind=type('SyntheticForeignNamespace',(),{foreign:target})
state=(target,target.__code__,None,None,(),None,())
entry=('target',target,(state,))
method=('probe',target,(state,))
cls=(kind,type(kind),kind.__mro__,tuple(vars(kind).items()),(method,))
witness=((space,(entry,)),)
native.register_code(0,(witness,(cls,),((space,(('target',target),)),)))
native.register_code(1,(witness,(),()))
for index in range(2,9):native.register_code(index,((),(),()))
active=True
assert native.verify_code() is False
assert events==['class lookup'] and 17 in space
''')
