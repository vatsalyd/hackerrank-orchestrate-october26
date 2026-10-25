"""Local OCR geometry binds identifiers to a row or a selected detail panel."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess

from .identifiers import RESOURCE, identifiers


def image_layout(path: Path, cache: Path):
    key=hashlib.sha256(b'ocr-layout-v1'+path.read_bytes()).hexdigest()
    destination=cache/'ocr'/(key+'.json')
    if destination.exists():
        return json.loads(destination.read_text(encoding='utf-8'))
    if os.name=='nt':
        result=subprocess.run(['powershell','-NoProfile','-File',str(Path(__file__).with_name('windows_ocr.ps1')),
            '-ImagePath',str(path.resolve()),'-AsJson'],capture_output=True,encoding='utf-8',timeout=40,check=True)
        layout=json.loads(result.stdout)
    elif shutil.which('tesseract'):
        result=subprocess.run(['tesseract',str(path),'stdout','tsv'],capture_output=True,
            encoding='utf-8',timeout=40,check=True)
        rows=list(csv.DictReader(io.StringIO(result.stdout),delimiter='\t'))
        page=next(row for row in rows if row['level']=='1')
        recognized=[row for row in rows if row['level']=='5' and row['text'].strip()]
        words=[dict(text=row['text'],x=float(row['left']),y=float(row['top']),
                    width=float(row['width']),height=float(row['height']))
               for row in recognized]
        lines={}
        for row in recognized:
            lines.setdefault((row['block_num'],row['par_num'],row['line_num']),[]).append(row['text'])
        layout={'width':int(page['width']),'height':int(page['height']),'words':words,
                'text':'\n'.join(' '.join(line) for line in lines.values())}
    else:
        raise ValueError('Install Tesseract for local image OCR')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(layout,ensure_ascii=False),encoding='utf-8')
    return layout


def grouped_rows(words):
    rows=[]
    for word in sorted(words,key=lambda item:(item['y']+item['height']/2,item['x'])):
        center=word['y']+word['height']/2
        if rows and abs(center-rows[-1][0])<=max(3,word['height']*.6):
            rows[-1][1].append(word)
        else:
            rows.append((center,[word]))
    return [sorted(words,key=lambda item:item['x']) for _,words in rows]


def row_text(words):
    return ' '.join(word['text'] for word in words)


def resource_words(row):
    for i,word in enumerate(row):
        token=word['text'].strip('.,:;()[]')
        if RESOURCE.fullmatch(token):
            yield token,word
            continue
        # Repair only adjacent visible fragments, without changing letters/digits.
        if i+1<len(row) and row[i+1]['x']-(word['x']+word['width'])<=max(12,word['height']):
            combined=token+row[i+1]['text'].strip('.,:;()[]')
            if RESOURCE.fullmatch(combined):
                yield combined,word


def subject_bindings(layout):
    """The selected panel wins over row text; activity history never supplies ownership."""
    words=layout['words']
    rows=grouped_rows(words)
    refs=[(resource,word,row) for row in rows for resource,word in resource_words(row)]
    panels={}
    labels={'owner','selector','account','email','phone','created','expires','size','status',
            'region','checksum','_index','display_name','customer_reference','indexed_at'}
    for ref,word,_ in refs:
        if word['x']<layout['width']*.65:
            continue
        bottom=min((other['y'] for other in words if other['x']>=layout['width']*.65
                    and other['y']>word['y']+word['height']
                    and other['text'].casefold() in {'activity','history'}),default=layout['height'])
        field_labels=[other for other in words if other['x']>=layout['width']*.65
                      and word['y']+word['height']<other['y']<bottom
                      and other['text'].casefold() in labels]
        if len({other['text'].casefold() for other in field_labels})>=2:
            panels[(ref,word['x'],word['y'])]=(min(other['x'] for other in field_labels)-12,bottom)
    boundary=min((left for left,_ in panels.values()),default=layout['width'])
    bindings={}
    for ref,word,row in refs:
        panel=panels.get((ref,word['x'],word['y']))
        if panel:
            left,bottom=panel
            selected=[other for other in words if other['x']>=left
                      and word['y']<=other['y']<bottom]
            text='\n'.join(row_text(items) for items in grouped_rows(selected))
            bindings[ref]={'identifiers':identifiers(text),'text':text,'scope':'selected_panel'}
        elif ref not in bindings:
            text=row_text([other for other in row if other['x']<boundary])
            bindings[ref]={'identifiers':identifiers(text),'text':text,'scope':'table_row'}
    return bindings
