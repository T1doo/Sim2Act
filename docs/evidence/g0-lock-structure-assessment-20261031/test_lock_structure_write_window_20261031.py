"""Actual lifecycle counterexample; not a business-authority acceptance test."""
from sqlalchemy import event
from sim2act.db import Store
from sim2act._immutable_settlement import OwnedValue
from sim2act._sqlite_model_snapshot import transaction,promote

def test_five_actual_writes_do_not_prove_python_callback_inputs_unchanged(tmp_path):
 store=Store('sqlite:///'+str(tmp_path/'write-window.db'),test_only=True,local_model_snapshots=True)
 store.initialize()
 with store.tx() as c:
  c.exec_driver_sql('CREATE TABLE diagnostic_payload (id INTEGER PRIMARY KEY,value INTEGER)')
  c.exec_driver_sql('INSERT INTO diagnostic_payload VALUES (1,0)')
 current={'complete':['synthetic','original']};saved=OwnedValue.capture(current);calls=[]
 def callback(c,cursor,statement,parameters,context,many):
  if statement.startswith('UPDATE diagnostic_payload'):
   calls.append(True)
   if len(calls)==5:current['complete'][1]='callback changed original input'
 try:
  with transaction(store) as c:
   assert c.exec_driver_sql('SELECT value FROM diagnostic_payload WHERE id=1').scalar_one()==0
   driver=c.connection.driver_connection;before=driver.total_changes
   event.listen(c,'before_cursor_execute',callback)
   try:
    promote(c)
    for value in range(1,6):c.exec_driver_sql('UPDATE diagnostic_payload SET value=? WHERE id=1',(value,))
    assert driver.total_changes-before==5 and len(calls)==5
    assert saved.matches(current) is False
    assert c.exec_driver_sql('SELECT value FROM diagnostic_payload WHERE id=1').scalar_one()==5
   finally:event.remove(c,'before_cursor_execute',callback)
  assert store._local_model_snapshot_records[-1]['outcome']=='COMMITTED'
 finally:store.engine.dispose()
