"""Explicit private installation selection, without migration or credential discovery."""
import json
import os
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
        if set(value)!={'format','runtime','data','credentials','workspace','model_key','live'} or value['format']!='sim2act.local-installation.v1' or type(value['live']) is not bool:
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
            'SIM2ACT_QUOTA_SUBJECT':'default-intern-account',
            'SIM2ACT_GOAL_PLANNER_PROVIDER':'intern-s2' if value['live'] else 'disabled',
        })
        return Settings.from_env(),database
    except Exception:
        raise ProtocolError('LOCAL_INSTALLATION_UNAVAILABLE') from None
