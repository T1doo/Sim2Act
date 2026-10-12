"""Actual cold HTTP source re-open after journal metadata is misbound; no mocks at API."""
import os,subprocess,json
from pathlib import Path
from sqlalchemy import update
from fastapi.testclient import TestClient
from test_registered_text_extraction import prepared
from test_registered_text_recovery_ui import page
from sim2act.db import Store,registered_extraction_requests as journal
from sim2act.api import create_app

OUT=Path('/tmp/pb-cold-recovery-review-20261011')
def test_cold_project_metadata_source_matches_actual_owned_run_before_install(env,tmp_path,monkeypatch):
    data,source,_,instance,run,target,resource,_=prepared(env)
    info={'project':data[4],'original_project':data[4],'source':source,'instance':instance['id'],'run':run['id'],'target':target,'resource':resource,'scenario':'poison-project-source','phase':'first','owner':'A'}
    original=subprocess.Popen
    def start(args,*a,**kw):
        if args[:2]==['node','tests/registered_text_recovery_ui.cjs']:args=[args[0],str(OUT/'poison_project_source_v2.cjs'),*args[2:]]
        return original(args,*a,**kw)
    monkeypatch.setattr(subprocess,'Popen',start);monkeypatch.setenv('SIM2ACT_COLD_EVIDENCE_DIR',str(OUT/'candidate2-independent-cold-pages'))
    first,worked=page(data[2],data[0],data[1],info,tmp_path);assert worked==0
    with data[0].tx() as c:c.execute(update(journal).values(source_app_id=target))
    data[2].close();cold=Store(data[1].database_url,test_only=True)
    try:
        with TestClient(create_app(cold,data[1])) as client:
            info['phase']='cold';page(client,cold,data[1],info,tmp_path)
    finally:cold.engine.dispose()
