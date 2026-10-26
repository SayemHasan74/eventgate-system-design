"""Independently audit declared Prisma foreign keys against Draw.io connectors."""
from pathlib import Path
import re,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
schema=(ROOT.parent/'eventgate-api/prisma/schema.prisma').read_text()
expected={}
for m in re.finditer(r'^model\s+(\w+)\s*\{([\s\S]*?)^\}',schema,re.M):
 name,body=m.groups();decl={}
 for line in body.splitlines():
  parts=line.strip().split(None,2)
  if len(parts)>=2 and not parts[0].startswith(('@@','//')):decl[parts[0]]=(parts[1],parts[2] if len(parts)>2 else '')
 for relation,(target,attrs) in decl.items():
  fields=re.search(r'@relation\([^\n]*?fields:\s*\[([^]]+)\]',attrs)
  if not fields:continue
  for fk in [x.strip() for x in fields.group(1).split(',')]:
   typ,scalarattrs=decl[fk];optional=typ.endswith('?');unique=bool(re.search(r'@(id|unique)\b',scalarattrs))
   expected[(name,fk,target.rstrip('?'))]={'parentPerChild':'0..1' if optional else '1','childrenPerParent':'0..1' if unique else '0..N'}
xml=ET.parse(ROOT/'diagrams/eventgate-erd.drawio');seen={};errors=[]
for page in xml.findall('diagram'):
 cells={c.attrib['id']:c for c in page.iter('mxCell')}
 for edge in cells.values():
  if edge.attrib.get('edge')!='1':continue
  a=edge.attrib;key=(a.get('schemaChild'),a.get('schemaForeignKey'),a.get('schemaParent'))
  if key not in expected:errors.append('Unexpected or untyped connector '+str(key));continue
  if cells[a['source']].attrib.get('schemaTable')!=key[2] or cells[a['target']].attrib.get('schemaTable')!=key[0]:errors.append('Connector endpoints reversed or incorrect '+str(key))
  for metric,value in expected[key].items():
   if a.get(metric)!=value:errors.append('Wrong cardinality '+str(key)+' '+metric)
  expected_label=expected[key]['parentPerChild']+' : '+expected[key]['childrenPerParent']
  if expected_label not in a.get('value',''):errors.append('Missing visible cardinality '+str(key))
  seen.setdefault(key,[]).append(page.attrib['name'])
for key in expected:
 if key not in seen:errors.append('Missing connector '+str(key))
report={'foreignKeys':len(expected),'represented':len(seen),'diagramViews':len(xml.findall('diagram')),'errors':errors,'relations':[{'child':k[0],'foreignKey':k[1],'parent':k[2],**v,'views':seen.get(k,[])} for k,v in expected.items()]}
(ROOT/'design/relationship-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='relations'},indent=2))
if errors:raise SystemExit(1)
