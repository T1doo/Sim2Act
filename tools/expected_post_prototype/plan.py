"""Owned whole-database data differential, NEVER a permission or G1 result.

Captures main ordinary tables including absence/ranges, not a list of seen IDs.
Only a separate in-memory clone receives replay writes. Original G1 is required.
Python, file, callback and unordered-query dependency closure is not claimed.
"""
from dataclasses import dataclass,field
import math,re,sqlite3,threading,time
from sqlalchemy.engine import Connection
from sim2act._immutable_settlement import OwnedValue,UnsupportedPlan

class Decline(ValueError):pass

_FUNCTION_QUERY='SELECT name,builtin,type,enc,narg,flags FROM pragma_function_list ORDER BY name,builtin,type,enc,narg,flags'
with sqlite3.connect(':memory:') as _native:
 _NATIVE_FUNCTIONS=tuple(_native.execute(_FUNCTION_QUERY).fetchall())
_native.close();del _native

@dataclass(frozen=True,slots=True)
class Bounds:
 """Collection caps/cooperative time checks, not peak-memory or SQL interrupts."""
 pages:int=8192
 rows:int=100000
 bytes:int=32*1024*1024
 seconds:float=5.
 def __post_init__(self):
  if (any(type(v) is not int or not 0<v<=maximum for v,maximum in ((self.pages,8192),(self.rows,100000),(self.bytes,32*1024*1024)))
      or type(self.seconds) not in (int,float) or not math.isfinite(self.seconds) or not 0<self.seconds<=5):raise Decline('invalid finite prototype bounds')

def _primitive(value):
 if type(value) not in (str,bytes,int,float,type(None)):raise Decline('nonprimitive SQL parameter')
 if type(value) is float and not math.isfinite(value):raise Decline('nonfinite SQL parameter')
 return value

def _quote(name):
 if type(name) is not str or '\x00' in name:raise Decline('unknown SQL identifier')
 return '"'+name.replace('"','""')+'"'

def _check_budget(end):
 if time.monotonic()>=end:raise Decline('shadow collection exceeded real time bound')

def schema(driver):
 rows=tuple(driver.execute('SELECT type,name,tbl_name,sql FROM main.sqlite_schema ORDER BY type,name,tbl_name,sql').fetchmany(4097))
 if len(rows)>4096 or sum(len(v)*4 for row in rows for v in row if type(v) is str)>4*1024*1024:raise Decline('schema collection bound')
 return rows

def preflight(driver,bounds,end):
 _check_budget(end)
 pages=driver.execute('PRAGMA page_count').fetchone()[0];page_size=driver.execute('PRAGMA page_size').fetchone()[0]
 if pages>bounds.pages or pages*page_size>bounds.bytes:raise Decline('database pages/bytes exceed preflight bound')

def environment(driver):
 if type(driver) is not sqlite3.Connection or driver.row_factory is not None or driver.text_factory is not str:raise Decline('unknown driver/row/text factory')
 databases=driver.execute('PRAGMA database_list').fetchall()
 if [r[1] for r in databases if r[1]!='temp']!=['main'] or driver.execute('SELECT count(*) FROM temp.sqlite_schema').fetchone()[0]:raise Decline('attached or temporary objects')
 functions=tuple(driver.execute(_FUNCTION_QUERY).fetchall())
 # These default SQLAlchemy functions are not invoked by the closed replay
 # grammar. Their implementation/other callbacks remain UNQUALIFIED for reuse.
 if any(r not in _NATIVE_FUNCTIONS and r[0] not in ('floor','regexp') for r in functions):raise Decline('unknown user SQL function inventory')
 collations=tuple(driver.execute('PRAGMA collation_list').fetchall())
 if {r[1] for r in collations}!={'BINARY','NOCASE','RTRIM'}:raise Decline('unknown collation')
 names=('encoding','foreign_keys','recursive_triggers','read_uncommitted','reverse_unordered_selects','schema_version','user_version','application_id')
 pragmas=tuple((name,tuple(driver.execute('PRAGMA '+name).fetchall())) for name in names)
 return (sqlite3.sqlite_version,pragmas,functions,collations)

def data_image(driver,expected_schema,bounds,end):
 expected_schema=schema_values(expected_schema)
 preflight(driver,bounds,end);catalog=schema(driver)
 if catalog!=expected_schema:raise Decline('unknown or changed complete schema')
 if any(r[0] in ('trigger','view') or r[3] and 'CREATE VIRTUAL TABLE' in r[3].upper() for r in catalog):raise Decline('trigger/view/virtual table')
 table_kinds=driver.execute('PRAGMA main.table_list').fetchall()
 if any(r[2] not in ('table',) for r in table_kinds if r[1]!='sqlite_schema'):raise Decline('virtual/shadow table')
 without_rowid={r[1]:bool(r[4]) for r in table_kinds}
 tables=[];count=size=0
 for kind,name,table,sql in catalog:
  if kind!='table':continue
  columns=tuple(driver.execute('SELECT * FROM pragma_table_xinfo(?)',(name,)).fetchall())
  if any(r[6] for r in columns):raise Decline('hidden/generated column')
  names={r[1].translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')) for r in columns}
  without=without_rowid[name]
  if without:
   keys=[r[1] for r in sorted(columns,key=lambda r:r[5]) if r[5]]
   if not keys:raise Decline('unknown WITHOUT ROWID key')
   fields='*';order=','.join(_quote(k) for k in keys)
  else:
   alias=next((k for k in ('_rowid_','rowid','oid') if k not in names),None)
   if alias is None:raise Decline('all rowid aliases shadowed')
   fields=_quote(alias)+',*';order=_quote(alias)
  cursor=driver.execute('SELECT '+fields+' FROM '+_quote(name)+' ORDER BY '+order)
  rows=[]
  while True:
   _check_budget(end);batch=cursor.fetchmany(min(128,bounds.rows-count+1))
   if not batch:break
   count+=len(batch)
   if count>bounds.rows:raise Decline('whole database row bound')
   for row in batch:
    for v in row:
     _primitive(v);size+=len(v)*4 if type(v) is str else len(v) if type(v) is bytes else 16
    if size>bounds.bytes:raise Decline('whole database byte bound')
    rows.append(tuple(row))
  indexes=tuple(driver.execute('SELECT * FROM pragma_index_list(?) ORDER BY seq',(name,)).fetchall())
  details=tuple((r[1],tuple(driver.execute('SELECT * FROM pragma_index_xinfo(?)',(r[1],)).fetchall())) for r in indexes)
  tables.append((name,columns,without,tuple(rows),indexes,details))
 _check_budget(end)
 return OwnedValue.capture((catalog,tuple(tables)))

def schema_values(value):
 if type(value) is not tuple or len(value)>4096:raise Decline('exact bounded schema required')
 rows=[];size=0
 for row in value:
  if type(row) is not tuple or len(row)!=4 or any(type(v) is not str for v in row[:3]) or type(row[3]) not in (str,type(None)):raise Decline('exact primitive schema fields required')
  size+=sum(len(v)*4 for v in row if type(v) is str)
  if size>4*1024*1024:raise Decline('schema collection bound')
  rows.append(tuple(v for v in row))
 return tuple(rows)

@dataclass(frozen=True,slots=True)
class Context:
 owner:str
 version:int
 epoch:int
 fence:int
 deadline_mono:float
 deadline_wall:float
 cancelled:bool=False
 revoked:bool=False
 def __post_init__(self):
  if (type(self.owner) is not str or not self.owner or len(self.owner)>256
      or any(type(v) is not int or v<0 for v in (self.version,self.epoch,self.fence))
      or type(self.cancelled) is not bool or type(self.revoked) is not bool
      or any(type(v) not in (int,float) or not math.isfinite(v) for v in (self.deadline_mono,self.deadline_wall))):raise Decline('exact finite context data required')

def context_values(context):
 if type(context) is not Context:raise Decline('unknown context')
 return (context.owner,context.version,context.epoch,context.fence,context.deadline_mono,context.deadline_wall,context.cancelled,context.revoked)

def context_current(before,current,write_count):
 if type(before) is not Context or type(current) is not Context:raise Decline('unknown context')
 if (before.owner!=current.owner or before.version!=current.version or before.fence!=current.fence
     or current.epoch!=before.epoch+write_count or current.cancelled or current.revoked
     or before.cancelled or before.revoked or before.deadline_mono!=current.deadline_mono
     or before.deadline_wall!=current.deadline_wall or time.monotonic()>=current.deadline_mono
     or time.time()>=current.deadline_wall):raise Decline('owner/version/epoch/revocation/cancel/time changed')

_IDENT=r'[A-Za-z_][A-Za-z0-9_]*'
_COL=_IDENT+r'(?:\.'+_IDENT+r')?'
_UPDATE=re.compile(r'UPDATE\s+('+_IDENT+r')\s+SET\s+'+_COL+r'\s*=\s*\?(?:\s*,\s*'+_COL+r'\s*=\s*\?)*\s+WHERE\s+'+_COL+r'\s*=\s*\?(?:\s+AND\s+'+_COL+r'\s*=\s*\?)*\s*',re.I)
_INSERT=re.compile(r'INSERT\s+INTO\s+('+_IDENT+r')\s*\(\s*'+_IDENT+r'(?:\s*,\s*'+_IDENT+r')*\s*\)\s*VALUES\s*\(\s*\?(?:\s*,\s*\?)*\s*\)\s*',re.I)

@dataclass(frozen=True,slots=True)
class Write:
 sql:str
 parameters:tuple
 rowcount:int
 changes:int
 def table(self):
  if type(self.sql) is not str or type(self.parameters) is not tuple or type(self.rowcount) is not int or type(self.changes) is not int:raise Decline('unknown write record')
  match=_UPDATE.fullmatch(self.sql) or _INSERT.fullmatch(self.sql)
  if match is None or self.sql.count('?')!=len(self.parameters):raise Decline('write outside closed native grammar')
  for v in self.parameters:_primitive(v)
  if self.rowcount!=1 or self.changes!=1:raise Decline('unexpected rowcount/hidden changes')
  return match.group(1)

@dataclass(frozen=True,slots=True)
class Plan:
 database:bytes=field(repr=False)
 before:OwnedValue=field(repr=False)
 inputs:OwnedValue=field(repr=False)
 environment:tuple=field(repr=False)
 shadow_environment:tuple=field(repr=False)
 schema:tuple=field(repr=False)
 context:OwnedValue=field(repr=False)
 bounds:tuple
 tables:tuple

@dataclass(frozen=True,slots=True)
class Result:
 status:str
 reason:str
 eligible_for_reuse:bool=field(default=False,init=False)
 closed_dependencies:tuple=('SQL_LOGICAL_MAIN_ENDPOINT',)
 missing_dependencies:tuple=('PYTHON_AND_FILE_CLOSURE','CALLBACK_AND_UDF_PROVENANCE','SQL_EXECUTION_ENVIRONMENT_QUALIFICATION','RAW_DRIVER_TX_BOUNDARIES','UNORDERED_QUERY_SEQUENCE','DYNAMIC_AUTHORIZATION')

class Observation:
 """Ephemeral actual connection ownership, deliberately absent from Plan."""
 def __init__(self,driver,transaction,context,inputs,expected_schema,tables,bounds=Bounds(),*,connection):
  if type(bounds) is not Bounds or type(tables) is not tuple or len(tables)!=5:raise Decline('explicit five-write table schedule required')
  if any(type(t) is not str or re.fullmatch(_IDENT,t) is None for t in tables):raise Decline('exact write table identifiers required')
  tables=tuple(t for t in tables);expected_schema=schema_values(expected_schema)
  bounds=Bounds(bounds.pages,bounds.rows,bounds.bytes,bounds.seconds)
  if (type(connection) is not Connection or connection.closed or connection.get_transaction() is not transaction or not transaction.is_active or connection.connection.driver_connection is not driver):raise Decline('actual connection transaction required')
  context_current(context,context,0)
  self.driver=driver;self.connection=connection;self.transaction=transaction;self.thread=threading.get_ident();self.active=True
  self._clone=None
  self.changes=driver.total_changes;end=time.monotonic()+bounds.seconds
  preflight(driver,bounds,end)
  env=environment(driver);before=data_image(driver,expected_schema,bounds,end)
  clone=sqlite3.connect(':memory:')
  try:
   def progress(status,remaining,total):
    _check_budget(end)
    if status not in (sqlite3.SQLITE_OK,sqlite3.SQLITE_DONE) or total>bounds.pages:raise Decline('bounded G0 backup refused')
   driver.backup(clone,pages=64,progress=progress,sleep=0.)
   if not before.matches(data_image(clone,expected_schema,bounds,end).materialize()):raise Decline('G0 backup logical data changed')
   raw=clone.serialize()
   if len(raw)>bounds.bytes:raise Decline('owned image byte bound')
   self.plan=Plan(raw,before,OwnedValue.capture(inputs),env,environment(clone),expected_schema,OwnedValue.capture(context_values(context)),(bounds.pages,bounds.rows,bounds.bytes,bounds.seconds),tables)
  except BaseException:
   clone.close();raise
  self._clone=clone
  self.writes=[]
 def close(self):
  self.active=False
  clone=self._clone;self._clone=None
  if clone is not None:clone.close()
 def record(self,sql,parameters,rowcount,changes,*,executemany=False):
  if not self.active or executemany or threading.get_ident()!=self.thread:raise Decline('write recorder lifecycle changed')
  write=Write(sql,parameters,rowcount,changes);table=write.table()
  if len(self.writes)>=5 or table!=self.plan.tables[len(self.writes)]:raise Decline('extra or reordered write')
  self.writes.append(write)
 def compare(self,driver,transaction,current,inputs):
  if not self.active:raise Decline('observation already closed')
  self.active=False
  try:
   if (driver is not self.driver or transaction is not self.transaction or threading.get_ident()!=self.thread or not driver.in_transaction
       or self.connection.closed or self.connection.get_transaction() is not self.transaction or not self.transaction.is_active
       or self.connection.connection.driver_connection is not driver):raise Decline('driver/transaction/thread changed')
   original=Context(*self.plan.context.materialize())
   context_current(original,current,len(self.writes))
   if len(self.writes)!=5 or driver.total_changes-self.changes!=5:raise Decline('actual write count changed')
   if not self.plan.inputs.matches(inputs):raise Decline('complete Python input data/alias changed')
   if environment(driver)!=self.plan.environment:raise Decline('SQL environment changed')
   bounds=Bounds(*self.plan.bounds);end=time.monotonic()+bounds.seconds
   actual=data_image(driver,self.plan.schema,bounds,end)
   clone=self._clone
   try:
    if type(clone) is not sqlite3.Connection or clone.in_transaction or environment(clone)!=self.plan.shadow_environment:raise Decline('shadow lifetime or environment changed')
    if not self.plan.before.matches(data_image(clone,self.plan.schema,bounds,end).materialize()):raise Decline('owned shadow data changed before replay')
    clone.execute('BEGIN')
    for write in self.writes:
     _check_budget(end);before=clone.total_changes;cursor=clone.execute(write.sql,write.parameters)
     if cursor.rowcount!=write.rowcount or clone.total_changes-before!=write.changes:raise Decline('replay rowcount changed')
    expected=data_image(clone,self.plan.schema,bounds,end)
    if not expected.matches(actual.materialize()):raise Decline('complete actual postimage differs')
   finally:self.close()
   context_current(original,current,len(self.writes))
   return Result('DATA_MATCH','Full logical SQLite endpoint only; original G1 required')
  except (Decline,sqlite3.Error,UnsupportedPlan) as error:return Result('DECLINE',str(error))
  finally:self.close()
