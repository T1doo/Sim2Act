"""Actual current-owner/project metadata fence before foreign P-B private reads."""
import json,os
from pathlib import Path
import pytest
from sqlalchemy import event,update
from test_registered_text_extraction import prepared,request,snapshot
from sim2act.db import runs

OUT=Path('/tmp/pb-text-extraction-review-20261011')
@pytest.mark.parametrize('fault',['foreign-owner','foreign-project'])
def test_foreign_extraction_api_scopes_metadata_before_private_run(env,fault):
    data,_,_,_,source,target,_,url=prepared(env)
    _,body=request(data,url,target)
    if fault=='foreign-project':
        unowned=data[0].project(env[4],'Synthetic unowned project for metadata gate')
        with data[0].tx() as c:c.execute(update(runs).where(runs.c.id==source['id']).values(project_id=unowned))
    else:data[2].headers['Authorization']='Bearer synthetic-test-B'
    before=snapshot(data[0]);statements=[];replies=[]
    def trace(c,cursor,statement,params,ctx,many):statements.append({'sql':statement,'params':params})
    event.listen(data[0].engine,'before_cursor_execute',trace)
    try:
        for method,path,payload in [('GET',url+'/extraction-options',None),('POST',url+'/extract',body),('GET',url+'/extraction-receipts?request_key='+body['request_key'],None)]:
            r=data[2].request(method,path,json=payload);replies.append({'method':method,'path':path,'status':r.status_code,'text':r.text})
    finally:event.remove(data[0].engine,'before_cursor_execute',trace)
    after=snapshot(data[0]);assert after==before
    violations=[row for row in statements if 'SELECT runs.id,' in row['sql'] and 'runs.context' in row['sql'] and 'runs.result' in row['sql'] and 'WHERE runs.id =' in row['sql']]
    p=OUT/(os.environ.get('PB_SCOPE_PREFIX','candidate3-foreign-private-green-')+fault+'.json');assert not p.exists()
    p.write_text(json.dumps({'classification':'ACTUAL_SQLITE_API_SQL_SCOPE_AUDIT','fault':fault,'responses':replies,'foreign_run_id':source['id'],'sql':statements,'private_run_selects':violations,'database_unchanged':after==before,'scope':'Three extraction routes, exact one fixture Run. Only SQL recorded, no foreign row payload exported.'},ensure_ascii=False,indent=2)+'\n')
    assert all(r['status']==403 for r in replies),replies
    assert not violations,'Private Run fields selected before owner/project metadata rejection'
