"""Export only this checkout's Codex traces, retaining JSONL after redaction."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

SECRETS = re.compile(r'\b(?:sk-or-v1-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{20,})\b')
EMAIL = re.compile(r'(?<![\w.!#$%&\x27*+/=?^`{|}~-])[\w.!#$%&\x27*+/=?^`{|}~-]{1,64}@[\w.-]{1,253}\.[A-Za-z]{2,63}')
PHONE = re.compile(r'(?<!\w)\+\d(?:[ ()-]*\d){6,14}(?!\d)')
PRIVATE_KEY = re.compile(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', re.DOTALL)
JWT = re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')
SECRET_FIELDS = {'api_key','apikey','access_token','refresh_token','password','passwd','client_secret','authorization','cookie','set-cookie','private_key'}


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {key: ('[REDACTED]' if key.casefold() in SECRET_FIELDS and isinstance(item,str) and item
                      else redact(item,secrets)) for key,item in value.items()}
    if isinstance(value, list):
        return [redact(item,secrets) for item in value]
    if not isinstance(value,str):
        return value
    if value.startswith('data:') and ';base64,' in value[:120]:
        return '[REDACTED BINARY PAYLOAD]'
    for secret in secrets:
        if secret:
            value=value.replace(secret,'[REDACTED]')
    for pattern in (PRIVATE_KEY,SECRETS,JWT):
        value=pattern.sub('[REDACTED]',value)
    if '@' in value:
        value=EMAIL.sub('[REDACTED EMAIL]',value)
    return PHONE.sub('[REDACTED PHONE]',value)


def export_trace(root, session_root, secrets=()):
    root,session_root=Path(root).resolve(),Path(session_root).resolve()
    destination=root/'agent-trace.zip'
    files=[]
    for source in sorted(session_root.rglob('rollout-*.jsonl')):
        try:
            with source.open(encoding='utf-8') as stream:
                first=json.loads(stream.readline())
            cwd=first.get('payload',{}).get('cwd')
            if not cwd or Path(cwd).resolve()!=root:
                continue
        except (OSError,ValueError):
            continue
        lines=source.read_text(encoding='utf-8').splitlines()
        cleaned=[]
        for index,line in enumerate(lines):
            try:
                record=json.loads(line)
            except ValueError:
                if index==len(lines)-1:
                    break  # A live append may leave one incomplete final record.
                raise
            cleaned.append(json.dumps(redact(record,secrets),ensure_ascii=False))
        data=('\n'.join(cleaned)+'\n').encode('utf-8')
        name='agent-trace/codex/sessions/'+source.relative_to(session_root).as_posix()
        files.append((name,data,len(cleaned)))
    if not files:
        raise ValueError('No Codex sessions match this checkout; refusing an empty trace archive')
    manifest={'captured_at':datetime.now(timezone.utc).isoformat(),
        'session_count':len(files),'live_snapshot':True,'files':[
            dict(path=name,records=count,sha256=hashlib.sha256(data).hexdigest()) for name,data,count in files]}
    notes=('This archive contains only Codex sessions whose recorded checkout matches this project.\n'
           'JSONL structure, timestamps and record order are preserved. Credentials, email addresses,\n'
           'phone numbers and inline binary payloads are redacted. Source traces are never modified.\n'
           'This is a snapshot of complete records while the agent is active; the final assistant\n'
           'message may not yet appear. Run python code/export_trace.py after closing the agent\n'
           'to refresh the snapshot, as recommended by agent_trace_instructions.md.\n')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data,_ in files:
            archive.writestr(name,data)
        if (root/'log.txt').exists():
            archive.writestr('agent-trace/log.txt',redact((root/'log.txt').read_text(encoding='utf-8'),secrets))
        archive.writestr('agent-trace/manifest.json',json.dumps(manifest,indent=2))
        archive.writestr('agent-trace/NOTES.txt',notes)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert all(not secret or all(secret.encode() not in archive.read(name) for name in archive.namelist()) for secret in secrets)
    return manifest


def main():
    root=Path(__file__).resolve().parents[1]
    session_root=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    names=('OPENROUTER_API_KEY','DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY',
           'GITHUB_TOKEN','GH_TOKEN','HF_TOKEN','HUGGING_FACE_HUB_TOKEN')
    manifest=export_trace(root,session_root,tuple(os.environ.get(name,'') for name in names))
    print(json.dumps({'archive':'agent-trace.zip','sessions':manifest['session_count'],'redacted':True}))


if __name__=='__main__':
    main()
