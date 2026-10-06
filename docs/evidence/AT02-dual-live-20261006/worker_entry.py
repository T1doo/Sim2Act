"""Normal one-shot LIVE worker with validation-only approved send boundary."""
import sys
from send_guard import Guard
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker
Guard(sys.argv[1]).install()
s = Settings.from_env()
store = Store(s.database_url)
try:
    assert Worker(store, s).once(), 'No owned intent claimed'
finally:
    store.engine.dispose()
