"""Build an allow-listed submission archive only after a complete valid run."""
import csv
import json
import sys
import zipfile
from pathlib import Path

from audit.models import Decision


def main():
    root=Path(__file__).resolve().parents[1]
    output=root/'output.csv'
    if not output.exists():
        raise SystemExit('Run the full audit successfully before packaging.')
    with output.open(encoding='utf-8',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames != ['case_id','deletion_status','steps_json']:
            raise SystemExit('Invalid output columns.')
        rows=list(reader)
    expected=sorted(row['case_id'] for row in csv.DictReader((root/'dataset/deletion_requests.csv').open(encoding='utf-8-sig',newline='')))
    if len(rows)!=518 or [row['case_id'] for row in rows]!=expected:
        raise SystemExit('Output must contain the complete sorted 518-case request set.')
    for row in rows:
        Decision(case_id=row['case_id'],deletion_status=row['deletion_status'],steps=json.loads(row['steps_json']))
    for report in ('evaluation_report.md','usage_report.md'):
        path=root/'code/evaluation'/report
        if not path.exists() or 'NOT A FINAL' in path.read_text(encoding='utf-8'):
            raise SystemExit(f'Final report missing or unfinished: {report}')
    files=[root/'README.md',root/'requirements.txt',root/'requirements-local.txt']
    files += [p for p in (root/'docs').rglob('*.md') if p.is_file()]
    files += [p for p in (root/'code').rglob('*') if p.is_file() and p.suffix in {'.py','.md','.ps1'}
        and '__pycache__' not in p.parts and '.venv' not in p.parts]
    destination=root/'code.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files): archive.write(path,path.relative_to(root).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert all(not name.startswith('dataset/') for name in archive.namelist())
    print(f'Created {destination.name}: {len(files)} files. Upload log.txt separately as the transcript.')


if __name__=='__main__':
    main()
