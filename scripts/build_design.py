from pathlib import Path
import re,json,math,textwrap,html,heapq,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'eventgate-api'
OUT=ROOT/'diagrams';OUT.mkdir(exist_ok=True)
SCHEMA=(SOURCE/'prisma/schema.prisma').read_text()
MODEL_BLOCKS=dict(re.findall(r'model (\w+)\s*\{(.*?)\n\}',SCHEMA,re.S))
ENUMS=set(re.findall(r'enum (\w+)',SCHEMA))
SCALARS={'String','Int','Boolean','DateTime','Json','BigInt','Float','Decimal','Bytes'}|ENUMS
models={};relationships=[]
for name,block in MODEL_BLOCKS.items():
 fields=[];foreign={}
 for target,keys in re.findall(r'^\s*\w+\s+(\w+)\??\s+@relation\([^\n]*?fields:\s*\[([^]]+)\]',block,re.M):
  for key in keys.split(','):foreign[key.strip()]=target
 for line in block.splitlines():
  m=re.match(r'\s*(\w+)\s+([\w?\[\]]+)(.*)',line)
  if not m:continue
  key,typ,attributes=m.groups()
  if typ.rstrip('?[]') not in SCALARS:continue
  flags=[]
  if '@id' in attributes:flags.append('PK')
  if key in foreign:flags.append('FK')
  if '@unique' in attributes:flags.append('UQ')
  fields.append({'name':key,'type':typ,'flags':flags,'target':foreign.get(key),'uuid':'@db.Uuid' in attributes})
  if key in foreign:relationships.append({'child':name,'field':key,'parent':foreign[key],'optional':'?' in typ,'unique':'@unique' in attributes or '@id' in attributes})
 constraints=re.findall(r'@@(unique|index)\(\[([^]]+)\]',block)
 models[name]={'fields':fields,'constraints':constraints}
(ROOT/'design/schema-summary.json').write_text(json.dumps(models,indent=2))

# Draw.io sources and lossless raster previews share the same diagram model.
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
class Diagram:
 def __init__(self,title,subtitle,w=1320,h=920):self.title=title;self.subtitle=subtitle;self.w=w;self.h=h;self.nodes=[];self.edges=[]
 def box(self,key,title,lines,x,y,w=340,h=None,color='#e9f1f8'):
  h=h or 48+len(lines)*24+12
  self.nodes.append(dict(key=key,title=title,lines=lines,x=x,y=y,w=w,h=h,color=color));return key
 def edge(self,a,b,label='',color='#557087',dashed=False):self.edges.append(dict(a=a,b=b,label=label,color=color,dashed=dashed))
 def route_edges(self):
  nodes={n['key']:n for n in self.nodes};used=set();counts={};label_rects=[]
  for e in self.edges:
   for k in ('a','b'):counts[e[k]]=counts.get(e[k],0)+1
  seen={}
  for e in self.edges:
   a,b=nodes[e['a']],nodes[e['b']]
   dx=b['x']+b['w']/2-a['x']-a['w']/2;dy=b['y']+b['h']/2-a['y']-a['h']/2
   sides=('right','left') if abs(dx)>abs(dy)*.8 and abs(dx)>40 else ('bottom','top')
   if sides[0]=='right' and dx<0:sides=('left','right')
   if sides[0]=='bottom' and dy<0:sides=('top','bottom')
   endpoints=[];ports=[]
   for node,side in zip((a,b),sides):
    idx=seen.get(node['key'],0);seen[node['key']]=idx+1
    fraction=.22+.56*(idx+1)/(counts[node['key']]+1)
    if side in ('right','left'):
     fx=1 if side=='right' else 0;fy=fraction;x=node['x']+fx*node['w'];y=round(node['y']+fy*node['h'],2);outside=(x+(12 if fx else -12),y)
    else:
     fx=fraction;fy=1 if side=='bottom' else 0;x=round(node['x']+fx*node['w'],2);y=node['y']+fy*node['h'];outside=(x,y+(12 if fy else -12))
    ports.append((fx,fy));endpoints.append(((x,y),outside))
   start,end=endpoints[0][1],endpoints[1][1]
   xs=sorted(set([12,self.w-12,start[0],end[0]]+[v for n in self.nodes for v in (n['x']-12,n['x']+n['w']+12)]))
   ys=sorted(set([85,self.h-12,start[1],end[1]]+[v for n in self.nodes for v in (n['y']-12,n['y']+n['h']+12)]))
   obstacles=[(n['x']-5,n['y']-5,n['x']+n['w']+5,n['y']+n['h']+5) for n in self.nodes]
   def clear(u,v):
    for l,t,r,bt in obstacles:
     if u[0]==v[0] and l<u[0]<r and max(min(u[1],v[1]),t)<min(max(u[1],v[1]),bt):return False
     if u[1]==v[1] and t<u[1]<bt and max(min(u[0],v[0]),l)<min(max(u[0],v[0]),r):return False
    return True
   init=(xs.index(start[0]),ys.index(start[1]),-1);goal=(xs.index(end[0]),ys.index(end[1]));queue=[(0,init)];dist={init:0};prev={};final=None
   while queue:
    cost,state=heapq.heappop(queue)
    if cost!=dist.get(state):continue
    xi,yi,direction=state
    if (xi,yi)==goal:final=state;break
    u=(xs[xi],ys[yi])
    for nx,ny,nd in [(xi-1,yi,0),(xi+1,yi,0),(xi,yi-1,1),(xi,yi+1,1)]:
     if nx<0 or nx>=len(xs) or ny<0 or ny>=len(ys):continue
     v=(xs[nx],ys[ny])
     if not clear(u,v):continue
     segment=tuple(sorted((u,v)));nc=cost+abs(u[0]-v[0])+abs(u[1]-v[1])+(24 if direction not in (-1,nd) else 0)+(160 if segment in used else 0)
     new=(nx,ny,nd)
     if nc<dist.get(new,1e20):dist[new]=nc;prev[new]=state;heapq.heappush(queue,(nc,new))
   if final is None:raise ValueError('No clear diagram route '+str(e))
   points=[];cur=final
   while True:
    points.append((xs[cur[0]],ys[cur[1]]))
    if cur==init:break
    cur=prev[cur]
   points.reverse()
   for u,v in zip(points,points[1:]):used.add(tuple(sorted((u,v))))
   allpoints=[endpoints[0][0]]+points+[endpoints[1][0]];simple=[]
   for point in allpoints:
    if len(simple)>1 and ((simple[-2][0]==simple[-1][0]==point[0]) or (simple[-2][1]==simple[-1][1]==point[1])):simple[-1]=point
    elif not simple or point!=simple[-1]:simple.append(point)
   e['points']=simple;e['ports']=ports
   if e['label']:
    measure=ImageDraw.Draw(Image.new('RGB',(1,1)));lines=e['label'].splitlines();lw=max(measure.textlength(line,font=font(13)) for line in lines)+10;lh=18*len(lines)+6
    total=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(simple,simple[1:]));remain=total/2;mid=simple[0]
    for u,v in zip(simple,simple[1:]):
     length=abs(u[0]-v[0])+abs(u[1]-v[1])
     if remain<=length:
      fraction=remain/length if length else 0;mid=(u[0]+fraction*(v[0]-u[0]),u[1]+fraction*(v[1]-u[1]));break
     remain-=length
    candidates=[]
    for u,v in zip(simple,simple[1:]):
     for frac in [.5,.25,.75]:
      cx=u[0]+frac*(v[0]-u[0]);cy=u[1]+frac*(v[1]-u[1])
      for dx,dy in [(dx,dy) for dx in [0,-40,40,-80,80,-120,120,-160,160,-200,200,-240,240,-280,280,-320,320] for dy in [0,-30,30,-60,60,-90,90]]:
       x=cx+dx;y=cy+dy;rect=(x-lw/2,y-lh/2,x+lw/2,y+lh/2)
       if rect[0]<10 or rect[1]<90 or rect[2]>self.w-10 or rect[3]>self.h-8:continue
       def overlap(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
       if any(overlap(rect,(n['x']-3,n['y']-3,n['x']+n['w']+3,n['y']+n['h']+3)) for n in self.nodes):continue
       if any(overlap(rect,(r[0]-3,r[1]-3,r[2]+3,r[3]+3)) for r in label_rects):continue
       candidates.append((abs(dx)+abs(dy)+.03*(abs(x-mid[0])+abs(y-mid[1])),x,y,rect))
    if not candidates:raise ValueError('No clear label placement '+str(e['label']))
    _,cx,cy,rect=min(candidates);e['labelCenter']=(cx,cy);e['labelOffset']=(cx-mid[0],cy-mid[1]);e['labelRect']=rect;label_rects.append(rect)
 def xml(self):
  self.route_edges()
  model=ET.Element('mxGraphModel',{'dx':str(self.w),'dy':str(self.h),'grid':'1','gridSize':'10','page':'1','pageWidth':str(self.w),'pageHeight':str(self.h),'background':'#ffffff'})
  root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
  for key,txt,y,size in [('title',self.title,15,27),('subtitle',self.subtitle,54,15)]:
   c=ET.SubElement(root,'mxCell',id=key,value=txt,style=f'text;html=0;align=left;verticalAlign=middle;fontSize={size};fontStyle={1 if key=="title" else 0};fontColor=#172d40;',vertex='1',parent='1');ET.SubElement(c,'mxGeometry',{'x':'28','y':str(y),'width':str(self.w-56),'height':'32','as':'geometry'})
  for n in self.nodes:
   value='<b>'+html.escape(n['title'])+'</b><br><br>'+'<br>'.join(html.escape(x) for x in n['lines'])
   c=ET.SubElement(root,'mxCell',id=n['key'],value=value,style=f'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=12;fontFamily=Arial;fontSize=17;fillColor={n["color"]};strokeColor=#657c8f;',vertex='1',parent='1')
   if 'table' in n:c.set('schemaTable',n['table'])
   ET.SubElement(c,'mxGeometry',{'x':str(n['x']),'y':str(n['y']),'width':str(n['w']),'height':str(n['h']),'as':'geometry'})
  for i,e in enumerate(self.edges):
   (ex,ey),(ix,iy)=e['ports']
   c=ET.SubElement(root,'mxCell',id='edge-'+str(i),value=html.escape(e['label']).replace('\n','<br>'),style=f'edgeStyle=none;rounded=0;html=1;fontSize=13;labelBackgroundColor=#ffffff;strokeColor={e["color"]};endArrow=block;endFill=1;exitX={ex};exitY={ey};entryX={ix};entryY={iy};exitPerimeter=0;entryPerimeter=0;dashed={int(e["dashed"])};',edge='1',parent='1',source=e['a'],target=e['b'])
   for attr in ['schemaChild','schemaForeignKey','schemaParent','parentPerChild','childrenPerParent']:
    if attr in e:c.set(attr,e[attr])
   if 'schemaForeignKey' in e:c.set('tooltip',e['schemaParent']+'.id -> '+e['schemaChild']+'.'+e['schemaForeignKey'])
   geo=ET.SubElement(c,'mxGeometry',{'relative':'1','x':'0','y':'0','as':'geometry'});
   if 'labelOffset' in e:
    ox,oy=e['labelOffset'];ET.SubElement(geo,'mxPoint',{'x':str(ox),'y':str(oy),'as':'offset'})
   arr=ET.SubElement(geo,'Array',{'as':'points'})
   for x,y in e['points'][1:-1]:ET.SubElement(arr,'mxPoint',{'x':str(x),'y':str(y)})

  return model
 def preview(self,path):
  scale=2;im=Image.new('RGB',(self.w*scale,self.h*scale),'white');d=ImageDraw.Draw(im)
  def text(x,y,s,size=18,bold=False,fill='#182f42'):d.text((x*scale,y*scale),s,font=font(size*scale,bold),fill=fill)
  text(28,18,self.title,27,True);text(28,58,self.subtitle,15)
  byid={x['key']:x for x in self.nodes}
  for i,e in enumerate(self.edges):
   pts=e['points']
   d.line([(int(x*scale),int(y*scale)) for x,y in pts],fill=e['color'],width=3)
   end,prev=pts[-1],pts[-2];theta=math.atan2(end[1]-prev[1],end[0]-prev[0]);p=[end,(end[0]-12*math.cos(theta-.45),end[1]-12*math.sin(theta-.45)),(end[0]-12*math.cos(theta+.45),end[1]-12*math.sin(theta+.45))];d.polygon([(x*scale,y*scale) for x,y in p],fill=e['color'])
   if e['label']:
    cx,cy=e['labelCenter'];lines=e['label'].splitlines();box=e['labelRect'];d.rectangle(tuple(value*scale for value in box),fill='white')
    for j,line in enumerate(lines):
     width=d.textlength(line,font=font(13*scale))/scale;text(cx-width/2,box[1]+3+j*18,line,13)


  for n in self.nodes:
   x,y,w,h=[n[k] for k in ('x','y','w','h')];d.rectangle((x*scale,y*scale,(x+w)*scale,(y+h)*scale),fill=n['color'],outline='#657c8f',width=2)
   text(x+12,y+10,n['title'],19,True);d.line(((x+10)*scale,(y+40)*scale,(x+w-10)*scale,(y+40)*scale),fill='#bdcbd5',width=2)
   for k,line in enumerate(n['lines']):text(x+12,y+49+24*k,line,17)
  im.save(path)

def write_diagrams(name,pages):
 f=ET.Element('mxfile',{'host':'app.diagrams.net','type':'device','version':'29.0.0'})
 for i,p in enumerate(pages):
  tab=ET.SubElement(f,'diagram',id=f'{name}-{i}',name=p.title);tab.append(p.xml());p.preview(OUT/f'{name}-{i+1}.png')
 ET.indent(f);ET.ElementTree(f).write(OUT/f'{name}.drawio',encoding='utf-8',xml_declaration=True)

# Each view has repeated anchors so all foreign-key relationships remain traceable.
views=[
 ('Commerce and inventory',['User','Event','TicketTier','SavedEvent','WaitlistEntry','Order']),
 ('Payments and refund settlement',['Order','PaymentAttempt','PaymentEvent','Refund','RefundActivity']),
 ('Identity and account preferences',['User','AuthIdentity','RefreshSession','PasswordReset','EmailVerification','NotificationPreference','EventPreference']),
 ('Notifications and operations',['User','Notification','NotificationDelivery','Job','RefundActivity','AuditLog','IdempotencyRecord','MaintenanceState','Refund']),
 ('Delivery reference relationships',['User','PasswordReset','EmailVerification','Notification','NotificationDelivery','Job']),
 ('Tickets ownership and admission staff',['User','Event','TicketTier','Order','Ticket']),
]
chosen={
 'User':['id','email','displayName','role','status','passwordHash','tokenVersion'],
 'Event':['id','organizerId','title','slug','startAt','endAt','status','deletedAt'],
 'TicketTier':['id','eventId','name','pricePaisa','capacity','reservedQuantity','soldQuantity','salesStartAt','salesEndAt'],
 'Order':['id','attendeeId','eventId','ticketTierId','quantity','totalAmountPaisaSnapshot','status','reservationExpiresAt','fulfilledPaymentAttemptId'],
 'PaymentAttempt':['id','orderId','sequence','merchantTransactionId','providerTransactionId','amountPaisa','status','replayOfAttemptId'],
 'PaymentEvent':['id','paymentAttemptId','providerEventKey','eventType','receivedAt','processedAt','payload'],
 'Ticket':['id','orderId','eventId','ticketTierId','attendeeId','sequence','qrToken','status','checkedInById'],
 'Refund':['id','orderId','paymentAttemptId','requestedById','reviewedById','amountPaisa','reason','status'],
 'Notification':['id','userId','type','sourceKey','reminderJobId','readAt','createdAt'],
 'NotificationDelivery':['id','notificationId','channel','state','idempotencyKey','passwordResetId','verificationId','nextAttemptAt'],
 'Job':['id','type','status','deduplicationKey','runAt','attempts','leaseExpiresAt'],
 'AuditLog':['id','actorId','action','entityType','entityId','createdAt'],
 'IdempotencyRecord':['id','userId','scope','key','requestHash','status','resourceId','expiresAt'],
 'MaintenanceState':['id','runToken','lastStartedAt','lastCompletedAt','heartbeatAt','processed','failed'],
}
ERDS=[]
for vi,(title,names) in enumerate(views):
 p=Diagram('EventGate ERD '+str(vi+1)+' '+title,'Arrow parent to child   |   a : b = parents per child : children per parent   |   PK key   FK foreign key   UQ unique   ? nullable',1500,1080)
 for i,name in enumerate(names):
  fields=models[name]['fields'];keep=chosen.get(name)
  if keep:fields=[f for k in keep for f in fields if f['name']==k]
  else:fields=fields[:8]
  lines=[]
  for f in fields:
   typ=f['type'].replace('String','uuid' if f['uuid'] else 'text').replace('DateTime','timestamp').replace('Boolean','bool')
   # Put a long identifier on its own line rather than shrink it.
   label=(' '.join(f['flags'])+' ' if f['flags'] else '')+f['name']
   if len(label+' '+typ)>37:lines.extend([label,'  '+typ])
   else:lines.append(label+'  '+typ)
  if name in ['SavedEvent','WaitlistEntry','TicketTier']:
   compound=[keys for kind,keys in models[name]['constraints'] if kind=='unique']
   for keys in compound:lines.append('UQ ('+keys+')')
  x=28+(i%3)*510;y=108+(i//3)*340
  p.box(name,name,lines,x,y,w=385,h=min(294,60+24*len(lines)),color='#e9f1f8' if name not in ['User','Order','Refund'] else '#eff4e9')
 for node in p.nodes:node['table']=node['key']
 if 'PaymentAttempt' in names:
  p.box('PaymentAttemptOriginal','PaymentAttempt same table alias',['PK id  uuid','UQ providerTransactionId  text?','Referenced by replayOfAttemptId','Alias only not an additional table'],1048,448,w=385,color='#fff3e6')
  p.nodes[-1]['table']='PaymentAttempt'
 roles={'organizerId':'organizer','userId':'user','eventId':'event','ticketTierId':'tier','attendeeId':'owner','checkedInById':'checked by','fulfilledPaymentAttemptId':'fulfillment','paymentAttemptId':'payment','orderId':'order','requestedById':'requested by','reviewedById':'reviewed by','replayOfAttemptId':'replay of','passwordResetId':'reset','verificationId':'verification','notificationId':'notification','reminderJobId':'job','actorId':'actor','refundId':'refund'}
 for rel in relationships:
  if rel['parent'] in names and rel['child'] in names:
   parent='PaymentAttemptOriginal' if rel['parent']==rel['child']=='PaymentAttempt' else rel['parent']
   child=rel['child'];left='0..1' if rel['optional'] else '1';right='0..1' if rel['unique'] else '0..N'
   label=roles.get(rel['field'],rel['field'])+'\n'+left+' : '+right
   p.edge(parent,child,label)
   p.edges[-1].update(schemaChild=child,schemaForeignKey=rel['field'],schemaParent=rel['parent'],parentPerChild=left,childrenPerParent=right)
 p.h=max(n['y']+n['h'] for n in p.nodes)+70
 ERDS.append(p)
write_diagrams('eventgate-erd',ERDS)

flow=Diagram('EventGate reservation and verified payment workflow','Solid arrows carry requests and results. Dashed arrows indicate asynchronous work. Database is authoritative.',1320,1160)
flow.box('client','1 Client and BFF',['Attendee selects tier and quantity','BFF attaches access token and CSRF','POST /api/v1/orders'],28,108,370)
flow.box('route','2 API route and middleware',['Request ID and rate limiting','Authenticate active attendee','Validate UUID, quantity and key'],473,108,370)
flow.box('controller','3 Order controller',['Read Idempotency-Key','Pass trusted attendee identity','Call createOrder service'],918,108,370)
flow.box('service','4 Order service',['Check idempotency and request hash','Lock event and ticket tier','Validate sale window and inventory'],918,405,370)
flow.box('db','5 Prisma and PostgreSQL',['Serializable transaction','Reserve stock and create order','Write idempotency record and audit'],473,405,370,color='#eff4e9')
flow.box('response','6 API response to client',['201 with authoritative order','Hold expires after 15 minutes','Error middleware formats failures'],28,405,370)
flow.box('checkout','7 Checkout and SSLCommerz',['Client requests hosted checkout','Persist attempt before provider call','200 checkout URL or 202 processing'],28,718,370)
flow.box('callback','8 Callback and background job',['Persist callback and deduplicate','Worker validates with provider API','Do not trust browser success URL'],473,718,370)
flow.box('fulfilled','9 Verified settlement',['Transaction settles stock and order','Issue one ticket per paid quantity','Client reads status and private QR'],918,718,370,color='#eff4e9')
for a,b,l in [('client','route','request'),('route','controller','validated request'),('controller','service','business command'),('service','db','read and write'),('db','response','commit or rollback'),('response','client','JSON response'),('response','checkout','next user action'),('checkout','callback','provider callback'),('callback','fulfilled','verified outcome')]:flow.edge(a,b,l,dashed=(a=='callback'))
flow.box('failure','Failure paths',['400 validation | 401 session | 403 role | 404 hidden resource | 409 stock, state or idempotency conflict','Provider uncertainty remains PROCESSING or UNKNOWN. A timeout is never interpreted as a successful payment.'],28,1040,1260,h=100,color='#fff3e6')
arch=Diagram('EventGate backend architecture','A modular monolith with a browser BFF, a relational source of truth and durable background work',1320,890)
arch.box('client','Client',['Browser or API consumer','Sends user intent','Renders success and retry states'],28,110,370)
arch.box('bff','Browser BFF',['Same origin browser endpoints','HttpOnly cookie and Redis session','CSRF checks for mutations'],473,110,370)
arch.box('api','Express API',['Request ID and rate limiting','JWT identity and active user checks','Role and schema middleware'],918,110,370)
arch.box('controller','Route and controller',['Map method and path to action','Extract validated input and identity','Format JSON and HTTP status'],918,395,370)
arch.box('service','Domain services',['Ownership and business rules','Idempotency and state transitions','Define transaction boundaries'],473,395,370)
arch.box('orm','Prisma and PostgreSQL',['Queries, constraints and relations','Row locks and serializable writes','Source of truth for stock and money'],28,395,370,color='#eff4e9')
arch.box('worker','Durable jobs and integrations',['Reservation expiry and reconciliation','SSLCommerz, Google and email','Leases, retry limits and audit trail'],28,680,815,h=155)
arch.box('errors','Central error handling',['AppError becomes safe envelope','Unexpected faults logged with ID','Secrets excluded from responses'],918,680,370,h=155,color='#fff3e6')
for a,b,l in [('client','bff','HTTPS'),('bff','api','Bearer API request'),('api','controller','validated request'),('controller','service','command or query'),('service','orm','data access'),('orm','worker','durable job state'),('worker','service','reconcile'),('service','errors','failure')]:arch.edge(a,b,l)
# The main SDA figure focuses on one complete request and response. The
# payment continuation is explained step by step in the document.
flow.nodes=[n for n in flow.nodes if n['key'] not in ['checkout','callback','fulfilled']]
flow.edges=[e for e in flow.edges if e['a'] not in ['checkout','callback','fulfilled'] and e['b'] not in ['checkout','callback','fulfilled']]
for n in flow.nodes:
 if n['key']=='failure':n['y']=570
 elif n['y']==405:n['y']=340
flow.title='EventGate ticket reservation workflow'
flow.subtitle='A complete client request through API layers to a committed inventory reservation and response'
flow.h=max(n['y']+n['h'] for n in flow.nodes)+25
for n in arch.nodes:
 if n['y']==395:n['y']=330
 elif n['y']==680:n['y']=550
arch.h=max(n['y']+n['h'] for n in arch.nodes)+25
for diagram in [flow,arch]:
 for edge in diagram.edges:
  if edge['label']!='JSON response':edge['label']=''
write_diagrams('eventgate-workflows',[flow,arch])

# Route inventory is grounded in router declarations and app mounts.
mounts={'authRouter':'/auth','healthRouter':'/health','publicEventsRouter':'/events','eventsRouter':'/organizer/events','ticketTiersRouter':'/organizer/events/:eventId/ticket-tiers','ordersRouter':'/orders','paymentsRouter':'/payments','sslcommerzCallbacksRouter':'/payments/sslcommerz','ticketsRouter':'/tickets','checkInRouter':'/organizer/events/:eventId/check-ins','attendeeRefundsRouter':'','adminRefundsRouter':'/admin','adminRouter':'/admin','usersRouter':'/users','adminReportsRouter':'/admin/reports','organizerReportsRouter':'/organizer/events/:eventId/reports','adminReadsRouter':'/admin','overviewRouter':'','notificationsRouter':'/notifications','notificationAccountRouter':'','savedEventsRouter':'/saved-events','recommendationsRouter':'','waitlistsRouter':'','aiRouter':'/ai'}
def access(router,path,method):
 if router=='sslcommerzCallbacksRouter':return 'Provider validation','SSLCommerz callback; not a user JWT'
 if router in ['healthRouter','publicEventsRouter','aiRouter']:return 'No','Public; rate limited where applicable'
 if router=='authRouter':
  if path=='/google/link':return 'Bearer','Any active user; link own identity'
  if path in ['/refresh','/logout']:return 'Refresh token','Token owner; not access JWT'
  if path=='/demo':return 'No','Attendee or organizer demo only when enabled'
  return 'No','Public'
 if router.startswith('admin') or path.startswith('/admin/'):return 'Bearer','ADMIN'
 if router in ['eventsRouter','ticketTiersRouter','checkInRouter','organizerReportsRouter'] or path=='/organizer/overview':return 'Bearer','ORGANIZER owns event; ADMIN may access'
 if router in ['usersRouter','notificationsRouter','notificationAccountRouter']:return 'Bearer','Any active user; own account only'
 return 'Bearer','ATTENDEE; own resources only'
def purpose(router,path,method):
 exact={('POST','/auth/register'):'Register an attendee account',('POST','/auth/login'):'Create an authenticated session',('POST','/auth/refresh'):'Rotate refresh token and access token',('POST','/auth/logout'):'Revoke a refresh session',('POST','/auth/demo'):'Start a restricted shared demo session',('GET','/auth/google/config'):'Read Google sign in availability',('POST','/auth/google'):'Sign in with verified Google identity',('POST','/auth/google/link'):'Link Google identity to own account',('POST','/auth/request-password-reset'):'Request account recovery email',('POST','/auth/reset-password'):'Reset password with a single use token',('POST','/orders'):'Reserve inventory and create an order',('GET','/events'):'Search and paginate published events',('GET','/events/facets'):'Read discovery cities and categories'}
 if (method,path) in exact:return exact[method,path]
 if '/sslcommerz/' in path:return 'Persist '+path.rsplit('/',1)[-1].upper()+' callback and schedule verification'
 suffix=path.rsplit('/',1)[-1]
 actions={'publish':'Publish a ready event','cancel':'Cancel the reservation or event','checkout':'Create or recover hosted checkout','qr':'Read private QR image','availability':'Read current reservable inventory','memberships':'Batch saved event membership reads','read-all':'Mark own notifications as read','email-verification':'Request email verification','confirm':'Confirm email verification token','reconcile':'Schedule provider verification','retry':'Queue a controlled recovery retry','orders/export':'Export authorized event order CSV','request-password-reset':'Request account recovery','maintenance':'Read maintenance status','operations':'Read operational incidents','statistics':'Read aggregate statistics','sales':'Read canonical revenue report','inventory':'Read current tier inventory','attendance':'Read issued and checked in counts','password':'Change password and revoke sessions','identity':'Read current authenticated identity','unread-count':'Read unread notification count','overview':'Read role specific dashboard summary','recommended':'Read personalized published event suggestions','search':'Interpret a natural language event search','ask':'Answer a question using public event facts','config':'Read optional feature availability','live':'Read process liveness','ready':'Read database readiness','status':'Change user account status' if method=='PATCH' else 'Read current check in window','role':'Change a user role','read':'Mark one notification read','bookings':'List complete purchased booking groups'}
 if path.endswith('/orders/export'):return actions['orders/export']
 if suffix in actions:return actions[suffix]
 stem=re.sub(r'/:[^/]+','',path).strip('/').replace('organizer/','').replace('admin/','').replace('users/me/','').replace('-',' ')
 return {'GET':'Read','POST':'Create','PUT':'Join or save','PATCH':'Update','DELETE':'Remove'}[method]+' '+stem
inventory=[]
for file in (SOURCE/'src/modules').rglob('*router.ts'):
 s=file.read_text()
 for m in re.finditer(r'(\w+)\.(get|post|patch|delete|put)\(\s*([\'\"])([^\'\"]+)\3',s):
  router,method,_,path=m.groups()
  if router not in mounts:continue
  full=(mounts[router]+('' if path=='/' else path)) or '/';auth,role=access(router,full,method.upper())
  # Authentication paths are compared relative to their own router.
  if router=='authRouter':auth,role=access(router,path,method.upper())
  inventory.append(dict(method=method.upper(),endpoint=full,purpose=purpose(router,full,method.upper()),auth=auth,role=role,source=str(file.relative_to(SOURCE))))
for method in ['GET','PUT','DELETE']:
 path='/events/:eventId/ticket-tiers/:tierId/waitlist';inventory.append(dict(method=method,endpoint=path,purpose={'GET':'Read own stock alert membership','PUT':'Join a stock alert without reserving stock','DELETE':'Leave a stock alert'}[method],auth='Bearer',role='ATTENDEE; own membership',source='src/modules/waitlists/waitlists.router.ts'))
inventory.sort(key=lambda x:(x['endpoint'],x['method']))
assert len({(x['method'],x['endpoint']) for x in inventory})==len(inventory)
(ROOT/'design/api-catalogue.json').write_text(json.dumps(inventory,indent=2))
print(f'Created {len(ERDS)} ERD views for {len(models)} schema entities and {len(inventory)} API operations; workflow has two views.')
