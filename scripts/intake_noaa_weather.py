"""Preserve user-supplied LCDv2 files and their hashes without inventing download times."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/bronze/noaa/lcdv2';BASE.mkdir(parents=True,exist_ok=True)
manifest=ROOT/'data/manifests/downloads.csv'
with manifest.open(newline='') as f:
 reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
for station in ['USW00014732','USW00094728','USW00094789']:
 name=f'LCD_{station}_2024.csv';source=Path.home()/'Downloads'/name;target=BASE/name
 data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
 if target.exists():assert target.read_bytes()==data,'Existing original differs; preserve as separate vintage'
 else:
  target.write_bytes(data)
  target.with_suffix('.intake.json').write_text(json.dumps({'user_supplied_path':str(source),'ingested_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':digest,'bytes':len(data),'source_url':None,'original_retrieved_at_utc':None,'note':'User supplied downloaded file; original download URL/time not established.'},indent=2)+'\n')
 row=dict(source_url='',retrieved_at_utc='',local_filename=str(target.relative_to(ROOT)),file_hash_sha256=digest,source_product='NOAA LCD v2 station-year CSV; user supplied',requested_period='2024',station_or_zone=station,provider='NOAA NCEI',model='',notes='User supplied from Downloads. Original download URL/time unknown; project intake timestamp recorded separately in .intake.json. Do not infer historical availability.')
 if not any(r['local_filename']==row['local_filename'] and r['file_hash_sha256']==digest for r in rows):rows.append(row)
 print(name,len(data),digest)
with manifest.open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
