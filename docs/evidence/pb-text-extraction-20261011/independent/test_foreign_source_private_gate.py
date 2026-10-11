"""Actual API SQL scope audit. One foreign owner, no raw payload export."""
import json
from pathlib import Path
from sqlalchemy import event
from test_registered_text_extraction import prepared

OUT=Path('/tmp/pb-text-extraction-review-20261011')
def test_foreign_extraction_api_scopes_metadata_before_private_run(env):
    data,_,_,_,source,_,_,url=prepared(env)
    statements=[]
    def trace(c,cursor,statement,params,ctx,many):
        statements.append({'sql':statement,'params':params})
    event.listen(data[0].engine,'before_cursor_execute',trace)
    try:
        data[2].headers['Authorization']='Bearer synthetic-test-B'
        response=data[2].get(url+'/extraction-options')
    finally:
        event.remove(data[0].engine,'before_cursor_execute',trace)
    assert response.status_code==403,response.text
    violations=[row for row in statements if 'SELECT runs.id,' in row['sql'] and 'runs.context' in row['sql'] and 'runs.result' in row['sql'] and 'WHERE runs.id =' in row['sql'] and 'runs.principal_id =' not in row['sql']]
    p=OUT/'candidate2-foreign-private-red.json'
    assert not p.exists()
    p.write_text(json.dumps({'classification':'ACTUAL_SQLITE_API_SQL_SCOPE_AUDIT','status':response.status_code,'response':response.text,'foreign_run_id':source['id'],'sql':statements,'private_unscoped_selects':violations,'scope':'One request to owned-by-A source using B credentials. SQL only; no foreign row payload copied.'},ensure_ascii=False,indent=2)+'\n')
    assert not violations,'Foreign source Run private fields selected before principal/project scope rejection'
