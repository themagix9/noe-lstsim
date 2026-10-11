"""Extract FPDF table text objects without merging overlapping columns.
One-off importer; requires pypdf, not a runtime dependency.
"""
import collections
import json
from pathlib import Path
import sys
from pypdf import PdfReader
from pypdf.generic import ContentStream
categories={'Akuttransport grün','Akuttransport gelb','Akuttransport rot','BLS/ALS aufwertbar','BLS grün','BLS gelb','BLS rot','ALS grün','ALS gelb','ALS orange','ALS rot','Telemedizin','Weitergabe','Großunfall','Alpinunfall'}
rows=[];pdf=PdfReader(sys.argv[1])
for number,page in enumerate(pdf.pages,1):
    values=[str(args[0]) for args,op in ContentStream(page.get_contents(),pdf).operations if op==b'Tj']
    for i,text in enumerate(values):
        if text.startswith(('RD-','ALP-')):
            if i+2>=len(values) or values[i+2] not in categories:raise ValueError(f'Unexpected row {number}: {text}')
            rows.append({'code':text,'title':values[i+1],'category':values[i+2],'page':number})
counts=collections.Counter(r['code'] for r in rows)
if any(n!=1 for n in counts.values()):raise ValueError('Duplicate codes')
Path(sys.argv[2]).write_text(json.dumps({'source':'Nutzer-PDF leoreport_ampds_codes_21022025.pdf','date':'2025-02-21','entries':rows},ensure_ascii=False,indent=2)+'\n')
print(len(rows),collections.Counter(r['category'] for r in rows))
