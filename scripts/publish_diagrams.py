"""Publish documentation only; credentials stay in the OS Git credential helper."""
import subprocess,os,json,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'},check=True)
credentials=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
headers={'Authorization':'Bearer '+credentials['password'],'User-Agent':'EventGate-design-delivery','Accept':'application/vnd.github+json'}
def api(path,body=None):
 req=urllib.request.Request('https://api.github.com'+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
 return json.load(urllib.request.urlopen(req,timeout=30))
owner=api('/user')['login'];name='eventgate-system-design';url=f'https://github.com/{owner}/{name}'
try:repo=api('/repos/'+owner+'/'+name)
except urllib.error.HTTPError as e:
 if e.code!=404:raise
 repo=api('/user/repos',{'name':name,'description':'EventGate backend system design with editable Draw.io ERD and workflow diagrams','private':False,'auto_init':False})
if repo['private']:raise RuntimeError('Existing repository is private; do not change its access automatically.')
if not (root/'.git').exists():
 subprocess.run(['git','init','-b','main'],cwd=root,check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','remote','add','origin',repo['clone_url']],cwd=root,check=True)
raw=f'https://raw.githubusercontent.com/{owner}/{name}/main/diagrams/eventgate-erd.drawio'
from urllib.parse import quote
links={'repository':repo['html_url'],'erd':'https://viewer.diagrams.net/?lightbox=1&nav=1&title=EventGate%20ERD#U'+quote(raw,safe=''),'workflow':'https://viewer.diagrams.net/?lightbox=1&nav=1#U'+quote(raw.replace('eventgate-erd','eventgate-workflows'),safe='')}
(root/'design/share-links.json').write_text(json.dumps(links,indent=2))
(root/'README.md').write_text('''# EventGate Backend System Design\n\nA documentation deliverable for the existing EventGate event management and ticketing project. No application code is changed.\n\n## Diagrams\n\n- [Open the ERD in Draw.io Viewer]('''+links['erd']+''')\n- [Open the SDA workflow and architecture in Draw.io Viewer]('''+links['workflow']+''')\n\nDownload the `.drawio` files in `diagrams/` to edit them in diagrams.net. The ERD has four named views, covers all 23 Prisma entities, and labels primary keys, foreign keys and unique constraints. Nullable foreign keys use `?`. Scalar pointers without a Prisma relation are not presented as enforced foreign keys. The document contains the complete foreign-key ledger, including links across views.\n\n## Design basis\n\nBackend source: [eventgate-api](https://github.com/SayemHasan74/eventgate-api), revision `f4f9396e83c317bc8b71e5a09762a1cd148ada9e`. API base `/api/v1`. The route inventory contains 109 API operations; it excludes browser BFF routes and infrastructure documentation endpoints. Request and response values in the document are illustrative design examples.\n\n## Written document\n\nThe complete Word document is in `deliverables/`. It covers the project, roles, eight core features, workflows, architecture, database, API catalogue, ten detailed contracts, and failure handling. It can be uploaded to Google Drive and opened as Google Docs.\n''')
(root/'.gitignore').write_text('.DS_Store\nqa/\n__pycache__/\n')
# Only the diagram and supporting data are published at this stage. The final
# verified Word deliverable is committed after its rendering review.
subprocess.run(['git','add','diagrams','design','scripts','README.md','.gitignore'],cwd=root,check=True)
subprocess.run(['git','commit','-m','Document EventGate data model and backend workflow diagrams'],cwd=root,check=True,stdout=subprocess.DEVNULL)
subprocess.run(['git','push','-u','origin','main'],cwd=root,check=True,stdout=subprocess.DEVNULL)
print(json.dumps(links,indent=2))
