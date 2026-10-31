"""Real SQLite data closure tests; no product authorization or cached G1."""
import dataclasses,sqlite3,time
import pytest
from sqlalchemy import create_engine
from tools.expected_post_prototype.plan import Bounds,Context,Decline,Observation,Write,schema,data_image

SCHEDULE=('items','audit','items','audit','items')
@pytest.fixture
def case(tmp_path):
 engine=create_engine('sqlite:///'+str(tmp_path/'facts.db'));connection=engine.connect();d=connection.connection.driver_connection;assert d.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
 d.executescript('''CREATE TABLE items(id INTEGER PRIMARY KEY AUTOINCREMENT,value TEXT);
 CREATE INDEX item_value ON items(value);
 CREATE TABLE audit(id TEXT PRIMARY KEY,payload BLOB);
 CREATE TABLE absent(id INTEGER PRIMARY KEY,value TEXT);
 CREATE TABLE ordered(a TEXT,b INTEGER,value TEXT,PRIMARY KEY(a,b)) WITHOUT ROWID;
 INSERT INTO items(value) VALUES('same'),('same');
 INSERT INTO ordered VALUES('x',2,'two'),('x',1,'one');''');d.commit();connection.exec_driver_sql('BEGIN')
 ctx=Context('synthetic-owner',1,7,2,time.monotonic()+20,time.time()+20)
 observed=[]
 try:yield d,connection.get_transaction(),ctx,{'left':[{'value':'synthetic'}]},schema(d),observed,connection
 finally:
  for o in observed:o.close()
  connection.rollback();connection.close();engine.dispose()

def observe(case,**options):
 d,tx,ctx,inputs,definition,observed,connection=case
 o=Observation(d,tx,ctx,inputs,definition,SCHEDULE,connection=connection,**options);observed.append(o);return o

def write_five(case,o):
 d=case[0]
 statements=[('UPDATE items SET value=? WHERE items.id=?',('one',1)),
  ('INSERT INTO audit (id,payload) VALUES (?,?)',('a',b'one')),
  ('UPDATE items SET value=? WHERE items.id=?',('two',2)),
  ('INSERT INTO audit (id,payload) VALUES (?,?)',('b',b'two')),
  ('UPDATE items SET value=? WHERE items.id=?',('three',1))]
 for sql,args in statements:
  before=d.total_changes;c=d.execute(sql,args);o.record(sql,args,c.rowcount,d.total_changes-before)
 return dataclasses.replace(case[2],epoch=case[2].epoch+5)

def finish(case,o,ctx):return o.compare(case[0],case[1],ctx,case[3])

def test_actual_uncommitted_five_write_matches_complete_clone(case):
 o=observe(case);ctx=write_five(case,o);result=finish(case,o,ctx)
 assert result.status=='DATA_MATCH' and result.eligible_for_reuse is False,result
 assert 'PYTHON_AND_FILE_CLOSURE' in result.missing_dependencies
 assert case[0].in_transaction
 with pytest.raises(Decline):finish(case,o,ctx)

@pytest.mark.parametrize('sql',[
 "INSERT INTO absent VALUES(1,'new missing-row/range member')",
 "DELETE FROM items WHERE id=2",
 "UPDATE ordered SET value='changed' WHERE a='x' AND b=1",
 "INSERT INTO items(value) VALUES('same')",
])
def test_unrecorded_add_delete_update_and_duplicate_decline(case,sql):
 o=observe(case);ctx=write_five(case,o);case[0].execute(sql)
 assert finish(case,o,ctx).status=='DECLINE'

def test_full_postimage_comparison_not_only_total_changes(case):
 o=observe(case);ctx=write_five(case,o)
 o.writes[4]=dataclasses.replace(o.writes[4],parameters=('different final recorded result',1))
 assert case[0].total_changes-o.changes==5
 assert finish(case,o,ctx).status=='DECLINE'

def test_equal_endpoint_does_not_claim_intermediate_write_equivalence(case):
 o=observe(case);ctx=write_five(case,o)
 # This different first result is overwritten by the subsequent second-row
 # update. Endpoint equality cannot establish identical intermediate effects.
 o.writes[0]=dataclasses.replace(o.writes[0],parameters=('overwritten intermediate',2))
 result=finish(case,o,ctx)
 assert result.status=='DATA_MATCH' and result.eligible_for_reuse is False

@pytest.mark.parametrize('damage',['content','split','merge'])
def test_python_input_content_and_alias_partition_are_checked(case,damage):
 shared=[{'value':'synthetic'}];case[3].clear();case[3].update(left=shared,right=shared if damage!='merge' else [{'value':'synthetic'}])
 o=observe(case);ctx=write_five(case,o)
 if damage=='content':shared[0]['value']='changed'
 elif damage=='split':case[3]['right']=[{'value':'synthetic'}]
 else:case[3]['right']=case[3]['left']
 assert finish(case,o,ctx).status=='DECLINE'

@pytest.mark.parametrize('values',[{'owner':'other'},{'version':2},{'fence':3},{'epoch':11},{'epoch':13},{'cancelled':True},{'revoked':True},{'deadline_mono':1.},{'deadline_wall':1.}])
def test_owner_version_epoch_fence_revoke_cancel_and_expiry_decline(case,values):
 o=observe(case);ctx=dataclasses.replace(write_five(case,o),**values)
 assert finish(case,o,ctx).status=='DECLINE'

def test_original_context_is_owned_not_a_borrowed_alias(case):
 o=observe(case);ctx=write_five(case,o);object.__setattr__(case[2],'owner','callback changed original owner')
 assert finish(case,o,dataclasses.replace(ctx,owner=case[2].owner)).status=='DECLINE'

@pytest.mark.parametrize('sql',['PRAGMA user_version=2','CREATE INDEX extra_index ON audit(payload)'])
def test_environment_or_schema_change_without_row_changes_declines(case,sql):
 o=observe(case);ctx=write_five(case,o);case[0].execute(sql)
 assert case[0].total_changes-o.changes==5
 assert finish(case,o,ctx).status=='DECLINE'

@pytest.mark.parametrize('ddl',[
 'CREATE TRIGGER unknown_trigger AFTER UPDATE ON items BEGIN UPDATE absent SET value=NEW.value; END',
 'CREATE VIEW unknown_view AS SELECT * FROM items',
 'CREATE TEMP TABLE unknown_temp(value)',
 "ATTACH DATABASE ':memory:' AS unknown_db",
])
def test_unknown_schema_and_attached_temp_decline_before_replay(case,ddl):
 case[0].execute(ddl)
 altered=(case[0],case[1],case[2],case[3],schema(case[0]),case[5],case[6])
 with pytest.raises(Decline):observe(altered)

def test_unknown_udf_is_not_invoked_or_scrubbed(case):
 calls=[];case[0].create_function('unknown_udf',1,lambda value:calls.append(value))
 with pytest.raises(Decline):observe(case)
 assert not calls

def test_unobservable_callback_provenance_never_provides_reuse(case):
 o=observe(case);ctx=write_five(case,o);case[3]['left'].append('external effect');case[3]['left'].pop()
 result=finish(case,o,ctx)
 assert result.status=='DATA_MATCH' and not result.eligible_for_reuse,result
 assert 'CALLBACK_AND_UDF_PROVENANCE' in result.missing_dependencies

@pytest.mark.parametrize('write',[Write('DELETE FROM items WHERE id=?',(1,),1,1),Write('UPDATE items SET value=unknown(?) WHERE id=?',('x',1),1,1),Write('UPDATE items SET value=? WHERE id=?; SELECT 1',('x',1),1,1),Write('UPDATE items SET value=? WHERE id=?',('x',1),0,0)])
def test_closed_replay_grammar_and_exact_rowcount(case,write):
 o=observe(case)
 with pytest.raises(Decline):o.record(write.sql,write.parameters,write.rowcount,write.changes)

def test_additional_record_or_executemany_cannot_be_hidden(case):
 o=observe(case);write_five(case,o)
 with pytest.raises(Decline):o.record('UPDATE items SET value=? WHERE id=?',('x',1),1,1)
 with pytest.raises(Decline):o.record('UPDATE items SET value=? WHERE id=?',('x',1),1,1,executemany=True)

def test_transaction_or_driver_rebinding_declines(case):
 o=observe(case);ctx=write_five(case,o)
 assert o.compare(case[0],object(),ctx,case[3]).status=='DECLINE'

@pytest.mark.parametrize('bounds',[Bounds(rows=1),Bounds(bytes=32),Bounds(pages=1)])
def test_complete_capture_respects_real_resource_bounds(case,bounds):
 with pytest.raises(Decline):observe(case,bounds=bounds)

def test_g0_backup_attempted_after_write_declines_without_wait_loop(case):
 case[0].execute("UPDATE items SET value='already a writer' WHERE id=1")
 started=time.monotonic()
 with pytest.raises(Decline):observe(case)
 assert time.monotonic()-started<2

@pytest.mark.parametrize('ddl',[
 'CREATE TABLE misleading(value TEXT DEFAULT \'WITHOUT ROWID\',key TEXT PRIMARY KEY)',
 'CREATE TABLE misleading("_ROWID_" TEXT,key TEXT)',
])
def test_real_rowid_is_retained_despite_ddl_text_or_case_insensitive_shadow(case,ddl):
 d=case[0];d.execute(ddl);d.execute("INSERT INTO misleading VALUES('same','same')")
 definition=schema(d);before=data_image(d,definition,Bounds(),time.monotonic()+5)
 # 'rowid' is the unshadowed alias in both fixtures. Visible columns do not
 # change; complete logical data still has to detect physical row identity.
 d.execute('UPDATE misleading SET rowid=99')
 after=data_image(d,definition,Bounds(),time.monotonic()+5)
 assert before.matches(after.materialize()) is False

def test_commit_begin_is_not_the_original_sqlalchemy_transaction(case):
 o=observe(case);ctx=write_five(case,o);case[6].commit();case[6].exec_driver_sql('BEGIN')
 assert finish(case,o,ctx).status=='DECLINE'

def test_borrowed_bounds_cannot_change_captured_collection_limits(case):
 bounds=Bounds();o=observe(case,bounds=bounds);object.__setattr__(bounds,'rows',1)
 ctx=write_five(case,o);assert finish(case,o,ctx).status=='DATA_MATCH'

def test_foreign_schema_comparison_is_not_dispatched(case):
 calls=[]
 class Foreign(tuple):
  def __eq__(self,other):calls.append(True);return True
 altered=(case[0],case[1],case[2],case[3],Foreign(case[4]),case[5],case[6])
 with pytest.raises(Decline):observe(altered)
 assert not calls

def test_same_rowcount_and_values_still_preserve_sqlite_integer_real_types(case):
 d=case[0];d.execute('CREATE TABLE mixed(value BLOB)');d.execute('INSERT INTO mixed VALUES (1)')
 definition=schema(d);before=data_image(d,definition,Bounds(),time.monotonic()+5)
 d.execute('UPDATE mixed SET value=1.0')
 after=data_image(d,definition,Bounds(),time.monotonic()+5)
 assert before.matches(after.materialize()) is False

def test_changed_shadow_does_not_replay_from_borrowed_state(case):
 o=observe(case);ctx=write_five(case,o);o._clone.execute("UPDATE ordered SET value='tampered'");o._clone.commit()
 assert finish(case,o,ctx).status=='DECLINE'
