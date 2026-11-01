"""Download/cache the three approved pilot months; never overwrites original ZIP bytes.

Run from the repository root: uv run python scripts/acquire_nyiso_pilot.py
Network access is required only for missing archives.
"""
from pathlib import Path
from datetime import datetime,timezone
import httpx,hashlib,csv,json,zipfile,time
root=Path(__file__).resolve().parents[1]
base=root/'data/bronze/nyiso/integrated_load';base.mkdir(parents=True,exist_ok=True)
manifest=root/'data/manifests/downloads.csv'
with manifest.open(newline='') as f: reader=csv.DictReader(f); fields=reader.fieldnames; records=list(reader)
for month in ['202401','202403','202411']:
 name=f'{month}01palIntegrated_csv.zip'; path=base/name
 url=f'https://mis.nyiso.com/public/csv/palIntegrated/{name}'
 if not path.exists():
  with httpx.Client(timeout=120,follow_redirects=True) as client:
   for attempt in range(3):
    try:
     r=client.get(url);r.raise_for_status();content=r.content
     import io
     with zipfile.ZipFile(io.BytesIO(content)) as z: assert z.testzip() is None
     path.write_bytes(content)
     stamp=datetime.now(timezone.utc).isoformat()
     metadata={'source_url':url,'retrieved_at_utc':stamp,'http_last_modified':r.headers.get('last-modified'),'http_etag':r.headers.get('etag'),'bytes':len(content)}
     path.with_suffix('.download.json').write_text(json.dumps(metadata,indent=2)+'\n')
     break
    except Exception:
     if attempt==2:raise
     time.sleep(attempt+1)
 meta=json.loads(path.with_suffix('.download.json').read_text())
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 record={'source_url':url,'retrieved_at_utc':meta['retrieved_at_utc'],'local_filename':str(path.relative_to(root)),'file_hash_sha256':digest,'source_product':'Integrated Real-Time Actual Load (P-58C)','requested_period':month[:4]+'-'+month[4:],'station_or_zone':'All source zones; NYC extracted for pilot','provider':'NYISO','model':'','notes':'Original monthly ZIP; current retrieved vintage, not historical first-publication vintage. Extracted-member lineage stored separately.'}
 if not any(x['local_filename']==record['local_filename'] and x['file_hash_sha256']==digest for x in records):records.append(record)
 with zipfile.ZipFile(path) as z:
  dest=base/'extracted'/month;dest.mkdir(parents=True,exist_ok=True)
  members=[]
  for member in z.infolist():
   if member.is_dir():continue
   memberpath=Path(member.filename)
   assert not memberpath.is_absolute() and '..' not in memberpath.parts
   data=z.read(member); target=dest/memberpath;target.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():assert target.read_bytes()==data
   else:target.write_bytes(data)
   members.append({'archive':record['local_filename'],'archive_sha256':digest,'member':member.filename,'local_filename':str(target.relative_to(root)),'member_sha256':hashlib.sha256(data).hexdigest()})
  (dest/'lineage.json').write_text(json.dumps(members,indent=2)+'\n')
 print(month,len(members),'members',len(path.read_bytes()),'bytes',digest)
with manifest.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(records)
