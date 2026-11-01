"""Cache January 2024 five-minute archive; extract two days for timing checks.

This auxiliary product never replaces the hourly integrated target.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,time,zipfile,io
import httpx
root=Path(__file__).resolve().parents[1]
base=root/'data/bronze/nyiso/timing_check';base.mkdir(parents=True,exist_ok=True)
manifest=root/'data/manifests/downloads.csv'
with manifest.open(newline='') as f:
 reader=csv.DictReader(f);fields=reader.fieldnames;records=list(reader)
path=base/'20240101pal_csv.zip';url=f'https://mis.nyiso.com/public/csv/pal/{path.name}'
if not path.exists():
 for attempt in range(3):
  try:
   r=httpx.get(url,timeout=120,follow_redirects=True);r.raise_for_status()
   with zipfile.ZipFile(io.BytesIO(r.content)) as z:assert z.testzip() is None
   path.write_bytes(r.content)
   path.with_suffix('.download.json').write_text(json.dumps({'source_url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'http_last_modified':r.headers.get('last-modified'),'bytes':len(r.content)},indent=2)+'\n')
   break
  except Exception:
   if attempt==2:raise
   time.sleep(attempt+1)
meta=json.loads(path.with_suffix('.download.json').read_text());digest=hashlib.sha256(path.read_bytes()).hexdigest()
record=dict(source_url=url,retrieved_at_utc=meta['retrieved_at_utc'],local_filename=str(path.relative_to(root)),file_hash_sha256=digest,source_product='Real-Time Actual Load (P-58B); timing cross-check only',requested_period='2024-01',station_or_zone='All source zones; NYC used for cross-check',provider='NYISO',model='',notes='Auxiliary archive, only January 15/16 extracted; does not replace hourly integrated target. Historical daily URL returned 404; monthly archive used.')
if not any(x['local_filename']==record['local_filename'] and x['file_hash_sha256']==digest for x in records):records.append(record)
lineage=[]
with zipfile.ZipFile(path) as z:
 for day in ['20240115','20240116']:
  name=day+'pal.csv';data=z.read(name);out=base/name
  if out.exists():assert out.read_bytes()==data
  else:out.write_bytes(data)
  lineage.append(dict(archive=record['local_filename'],archive_sha256=digest,member=name,member_sha256=hashlib.sha256(data).hexdigest(),local_filename=str(out.relative_to(root))))
(base/'lineage.json').write_text(json.dumps(lineage,indent=2)+'\n')
with manifest.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(records)
print(path.name,len(path.read_bytes()),digest)
