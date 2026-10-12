import sys,json,tempfile
from pathlib import Path
import pytest
from sqlalchemy import delete,update
from test_text_continuations import open_legacy,prepared,path,rows
from sim2act.db import internal_instance_data,internal_instances
from sim2act.text_continuations import implementation
proofs=[]
for name in ("233","a747"):
 patch=pytest.MonkeyPatch();tmp=Path(tempfile.mkdtemp(prefix="missing-typed-old-"));opened=open_legacy(name,tmp,patch);data=next(opened);store,settings,client,info=data
 try:
  with store.tx() as c:
   c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id==info["instance"]["id"]))
   c.execute(update(internal_instances).where(internal_instances.c.id==info["instance"]["id"]).values(data_version=0))
  before=rows(store);approval,request,commit=prepared(data)
  reply=client.post(path(info),json=commit)
  cold=client.get("/api/internal/instances/"+info["instance"]["id"]+"/runs/"+info["successful_old_run_id"])
  proofs.append(dict(anchor=name,implementation=implementation(),preflight_status=201,commit_status=reply.status_code,cold_successful_run_status=cold.status_code,cold_error=cold.json(),model_requests=0,original_successful_worker_and_receipt_preserved=True,typed_missing_and_data_version_zero=True,old_payloads_re_signed=False))
  assert reply.status_code==201 and cold.status_code==409,(reply.text,cold.text)
 finally:
  opened.close();patch.undo()
Path(sys.argv[1]).write_text(json.dumps(proofs,indent=2)+"\n")
print(json.dumps(proofs,indent=2))
