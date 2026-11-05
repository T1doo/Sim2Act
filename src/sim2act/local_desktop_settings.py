"""Explicit private installation selection, without migration or credential discovery."""
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from .config import Settings
from .desktop_protocol import ProtocolError, ordinary
from .private_postgres import PrivatePostgres
from .windows_credentials import read_dpapi


def local_settings(path):
    try:
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError
                result[key]=value
            return result
        value=json.loads(ordinary(path).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
        required={'format','runtime','data','credentials','workspace','model_key','live'}
        optional={'generation_enabled','generation_approval','generation_run_selection','production_account'}
        if not required.issubset(value) or set(value)-required-optional or value['format']!='sim2act.local-installation.v1' or type(value['live']) is not bool:
            raise ValueError
        generation=value.get('generation_enabled',False)
        production_account=value.get('production_account')
        quota_subject='default-intern-account'
        if production_account is not None:
            from .production_evidence import ACCOUNT_ID
            from .production_trial_admission import canonical_quota_subject
            if production_account!=ACCOUNT_ID or not value['live'] or generation is not True:raise ValueError
            quota_subject=canonical_quota_subject(ACCOUNT_ID)
        approval=value.get('generation_approval','')
        run_selection=value.get('generation_run_selection',False)
        if type(run_selection) is not bool or (run_selection and not generation):raise ValueError
        if type(generation) is not bool or not isinstance(approval,str) or (approval and (not generation or not re.fullmatch(r'gaapproval_[a-f0-9]{32}',approval))):
            raise ValueError
        for key in ('runtime','data','credentials','workspace'):
            if not isinstance(value[key],str) or not Path(value[key]).is_absolute():raise ValueError
            ordinary(value[key])
        database=PrivatePostgres(value['runtime'],value['data'])
        credentials=json.loads(read_dpapi(value['credentials']),object_pairs_hook=unique)
        if credentials.get('data_dir')!=value['data'] or credentials.get('port')!=database.port:
            raise ValueError
        password=credentials.get('app_password')
        if not isinstance(password,str) or not password:raise ValueError
        token=''
        if value['live']:
            if not isinstance(value['model_key'],str) or not Path(value['model_key']).is_absolute():raise ValueError
            token=read_dpapi(value['model_key'])
            if not token:raise ValueError
        os.environ.update({
            'SIM2ACT_DATABASE_URL':f'postgresql+psycopg://sim2act_app:{quote(password,safe="")}@127.0.0.1:{database.port}/sim2act_local',
            'SIM2ACT_DATA_DIR':value['workspace'],
            'SIM2ACT_MODEL_MODE':'live' if value['live'] else 'mock',
            'SIM2ACT_LIVE_ENABLED':str(value['live']).lower(),
            'SIM2ACT_MODEL':'intern-s2',
            'SIM2ACT_INTERN_TOKEN':token,
            'INTERN_API_TOKEN':'',
            'SIM2ACT_QUOTA_SUBJECT':quota_subject,
            'SIM2ACT_GOAL_PLANNER_PROVIDER':'intern-s2' if value['live'] else 'disabled',
            'SIM2ACT_NATURAL_ACTIVATION_ENABLED':'false',
            'SIM2ACT_NATURAL_ACTIVATION_LIVE_ID':'',
            'SIM2ACT_APPLICATION_GENERATION_ACTIVATION_ENABLED':str(generation).lower(),
            'SIM2ACT_APPLICATION_GENERATION_LIVE_ID':approval,
            'SIM2ACT_APPLICATION_GENERATION_RUN_SELECTION':str(run_selection).lower(),
        })
        return Settings.from_env(),database
    except Exception:
        raise ProtocolError('LOCAL_INSTALLATION_UNAVAILABLE') from None
