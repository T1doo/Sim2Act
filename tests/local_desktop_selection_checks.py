"""Synthetic settings projection only; no DPAPI reads, database or model calls."""
import json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sim2act.local_desktop_settings import local_settings
from sim2act.desktop_protocol import ProtocolError

checks=[]
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    value=dict(format='sim2act.local-installation.v1',runtime=str(root/'runtime'),data=str(root/'data'),credentials=str(root/'credentials'),workspace=str(root/'workspace'),model_key=None,live=False)
    selected=root/'selection.json'
    class FakeDatabase:
        def __init__(self,*args):self.port=55432
    with patch('sim2act.local_desktop_settings.PrivatePostgres',FakeDatabase),patch('sim2act.local_desktop_settings.read_dpapi',return_value=json.dumps({'data_dir':value['data'],'port':55432,'app_password':'synthetic'})),patch.dict(os.environ,{},clear=True):
        os.environ['SIM2ACT_APPLICATION_GENERATION_LIVE_ID']='gaapproval_'+'a'*32
        os.environ['SIM2ACT_NATURAL_ACTIVATION_LIVE_ID']='nlactivation_'+'b'*32
        selected.write_text(json.dumps(value))
        settings,_=local_settings(selected)
        assert not settings.application_generation_activation_enabled and not settings.application_generation_live_id and not settings.natural_activation_live_id
        checks.append('unselected inherited activation IDs cleared')
        selected.write_text(json.dumps({**value,'generation_enabled':True}))
        settings,_=local_settings(selected)
        assert settings.application_generation_activation_enabled and not settings.application_generation_live_id
        checks.append('enabling preparation alone selects no LIVE approval')
        selected.write_text(json.dumps({**value,'generation_enabled':True,'generation_approval':'gaapproval_'+'c'*32}))
        settings,_=local_settings(selected)
        assert settings.application_generation_live_id=='gaapproval_'+'c'*32
        checks.append('explicit well-formed approval selection preserved without minting permission')
        for extra in ({'generation_enabled':'true'},{'generation_approval':'gaapproval_'+'c'*32},{'generation_enabled':True,'generation_approval':'anything'},{'unexpected':True}):
            selected.write_text(json.dumps({**value,**extra}))
            try:local_settings(selected)
            except ProtocolError:checks.append('invalid selection rejected: '+','.join(extra))
            else:raise AssertionError('Invalid selection accepted')
print({'status':'PASS','checks':checks,'scope':'synthetic settings projection, not approval validity or P-A execution'})
