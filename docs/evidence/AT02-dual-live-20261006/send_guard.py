"""Linux validation-only send boundary; normal httpx TLS/proxy/identity preserved."""
import fcntl
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from sim2act.errors import DomainError
from sim2act.model import normalize_usage, parse_response, require_returned_model, returned_model_identity
from sim2act.tools import definitions

ENDPOINT = 'https://chat.intern-ai.org.cn/api/v1/chat/completions'


def utc():
    return datetime.now(timezone.utc).isoformat()


class Guard:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / 'wire.json'

    def save(self, data):
        tmp = self.path.with_suffix('.tmp')
        with tmp.open('w', encoding='utf-8') as stream:
            stream.write(json.dumps(data, indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(self.path)
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def send(self, original, client, request, **kwargs):
        # Never inspect request headers, credentials, environment or private reasoning.
        if str(request.url) != ENDPOINT or request.method != 'POST':
            raise DomainError('UNSUPPORTED_CAPABILITY', 'Only approved fixed model endpoint')
        body = json.loads(request.content)
        manifest = json.loads((self.root / 'fixture.json').read_text())
        users = [m for m in body['messages'] if m['role'] == 'user']
        context = json.loads(users[0]['content']) if len(users) == 1 else {}
        own = next((x for x in manifest['groups'] if context.get('resource_refs') == [x['resource_id']]), None)
        valid = (own is not None and context.get('goal') == 'Read; echo.'
                 and body.get('model') == 'intern-s2' and body.get('max_tokens') == 512
                 and body.get('stream') is False and body.get('tools') == definitions()
                 and len(request.content.decode('utf-8')) <= 2000
                 and all(x['resource_id'] not in request.content.decode('utf-8') for x in manifest['groups'] if x != own))
        with (self.root / 'wire.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text())
            if not valid or data['halted'] or len(data['requests']) >= 4:
                data['blocked'].append({'utc': utc(), 'reason': 'shape/scope/size' if not valid else 'halted' if data['halted'] else 'global four-send cap'})
                self.save(data)
                raise DomainError('BUDGET_EXHAUSTED', 'Approved send guard refused before network')
            delay = max(0, 6 - (time.time() - data.get('last_response_at', 0)))
            if delay:
                time.sleep(delay)  # <=6 seconds, global lock serializes both workers.
            record = {'sequence': len(data['requests'])+1, 'group': own['label'],
                      'start_utc': utc(), 'input_characters': len(request.content.decode()),
                      'utf8_bytes': len(request.content), 'request_sha256': hashlib.sha256(request.content).hexdigest(),
                      'requested_model': 'intern-s2', 'max_tokens':512, 'stream':False,
                      'seconds_since_previous_response': None if not data['requests'] else time.time()-data['last_response_at'],
                      'outcome':'SENDING_OR_UNKNOWN', 'usage':{'status':'unknown','tokens':None}}
            data['requests'].append(record)
            data['halted'] = True  # Crash/unknown cannot silently allow another send.
            self.save(data)  # Conservative slot durable BEFORE original transport.
            try:
                response = original(client, request, **kwargs)  # exactly one normal send; no retry wrapper.
                response.read()
                record.update(end_utc=utc(), http_status=response.status_code, outcome='RESPONSE_RECEIVED')
                semantic_valid = False
                try:
                    raw=response.json()
                    record['response_model']=raw.get('model') if isinstance(raw.get('model'),str) else None
                    record['usage']=normalize_usage(raw)
                    require_returned_model(returned_model_identity('intern-s2', record['response_model']))
                    parse_response(raw)
                    semantic_valid = True
                except (ValueError,TypeError,AttributeError,DomainError):
                    record['response_model']=None
                data['last_response_at']=time.time()
                record['semantic_valid'] = semantic_valid
                data['halted']=response.status_code != 200 or not semantic_valid
                self.save(data)
                return response
            except BaseException as error:
                record.update(end_utc=utc(), outcome='FAILED_OR_UNKNOWN', error_type=type(error).__name__)
                data['last_response_at']=time.time()
                self.save(data)
                raise

    def install(self):
        import httpx
        original = httpx.Client.send
        guard = self
        def bounded(client, request, **kwargs):
            return guard.send(original, client, request, **kwargs)
        httpx.Client.send = bounded
