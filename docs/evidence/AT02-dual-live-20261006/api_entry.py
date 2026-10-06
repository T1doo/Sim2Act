"""Owned validation API process; application CRUD role, no schema creation."""
import sys
import uvicorn
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
s = Settings.from_env()
uvicorn.run(create_app(Store(s.database_url), s), host='127.0.0.1', port=int(sys.argv[1]), log_level='error', access_log=False)
