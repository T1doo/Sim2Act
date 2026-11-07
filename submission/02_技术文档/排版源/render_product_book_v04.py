from pathlib import Path
import runpy, json, hashlib, html
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'submission/02_技术文档'
OUT.mkdir(exist_ok=True)
PAGES=json.loads((OUT/'产品书内容结构_v04.json').read_text(encoding='utf-8'))
PDF=OUT/'Sim2Act_产品书_审阅版_v04.pdf'
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc'))
pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc'))
W,H=595.276,841.89
M=40; CW=W-2*M
NAVY=colors.HexColor('#132640'); BLUE=colors.HexColor('#255ce0'); PURPLE=colors.HexColor('#785de8'); TEAL=colors.HexColor('#008f9b'); GRAY=colors.HexColor('#51647b'); LINE=colors.HexColor('#d9e2ef'); PALE=colors.HexColor('#eef4fd')
styles={
'title':ParagraphStyle('title',fontName='CNB',fontSize=22,leading=30,textColor=NAVY,wordWrap='CJK'),
'lead':ParagraphStyle('lead',fontName='CN',fontSize=11.3,leading=18,textColor=GRAY,wordWrap='CJK'),
'head':ParagraphStyle('head',fontName='CNB',fontSize=11.2,leading=17,textColor=NAVY,wordWrap='CJK'),
'body':ParagraphStyle('body',fontName='CN',fontSize=10.6,leading=17.4,textColor=NAVY,wordWrap='CJK'),
'small':ParagraphStyle('small',fontName='CN',fontSize=8.0,leading=12.5,textColor=GRAY,wordWrap='CJK'),
'cell':ParagraphStyle('cell',fontName='CN',fontSize=9.5,leading=15,textColor=NAVY,wordWrap='CJK'),
'cellhead':ParagraphStyle('cellhead',fontName='CNB',fontSize=9.2,leading=14,textColor=NAVY,wordWrap='CJK'),
'node':ParagraphStyle('node',fontName='CNB',fontSize=10.2,leading=16,textColor=NAVY,wordWrap='CJK',alignment=1),
'node_small':ParagraphStyle('node_small',fontName='CN',fontSize=8.5,leading=12.5,textColor=GRAY,wordWrap='CJK',alignment=1)
}
c=canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('Sim2Act：让构想成为可用的应用 | 产品书审阅版')
c.setAuthor('Sim2Act')
layout=[]

def para(text,x,y,w,kind='body'):
    p=Paragraph(html.escape(text).replace('\n','<br/>'),styles[kind]); _,h=p.wrap(w,1000)
    p.drawOn(c,x,y-h); return y-h

def header(num,p):
    c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(BLUE);c.rect(0,H-7,W*.6,7,fill=1,stroke=0)
    c.setFillColor(PURPLE);c.rect(W*.6,H-7,W*.4,7,fill=1,stroke=0)
    c.setFont('CNB',9);c.setFillColor(BLUE);c.drawString(M,H-35,p['kicker'])
    c.setFont('CN',8);c.setFillColor(GRAY);c.drawRightString(W-M,H-35,'Sim2Act / 产品书')
    y=para(p['title'],M,H-55,CW,'title')-12
    y=para(p['lead'],M,y,CW,'lead')-16
    c.setStrokeColor(LINE);c.line(M,38,W-M,38)
    c.setFont('CN',7.5);c.setFillColor(GRAY);c.drawString(M,24,'方向3 · 开放赋能智能体  |  2026.11.07 · 审阅版')
    c.setFont('CNB',9);c.drawRightString(W-M,23,f'{num:02d} / 16')
    return y

def image_path(name):
    folder='03_图片与截图/技术图_v02' if name.startswith(('ARCH-','T1-','T2-','T3-','T4-')) else ('03_图片与截图/实际运行' if name.startswith('E_') else '04_视频/生成图片')
    return ROOT/'submission'/folder/name

def screenshot(name,y,height=216):
    p=image_path(name);im=ImageReader(str(p));iw,ih=im.getSize(); w=min(CW,height*iw/ih);h=w*ih/iw
    x=M+(CW-w)/2
    c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(M,y-h-8,CW,h+8,7,fill=1,stroke=1)
    c.drawImage(im,x,y-h,width=w,height=h,mask='auto')
    return y-h-19

def arrow(x1,y1,x2,y2,color=BLUE):
    c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(1.1);c.line(x1,y1,x2,y2)
    import math
    a=math.atan2(y2-y1,x2-x1);sz=4
    p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-sz*math.cos(a-.5),y2-sz*math.sin(a-.5));p.lineTo(x2-sz*math.cos(a+.5),y2-sz*math.sin(a+.5));p.close();c.drawPath(p,fill=1,stroke=0)

def node(x,y,w,h,title,sub='',accent=BLUE):
    c.setFillColor(colors.white);c.setStrokeColor(LINE);c.roundRect(x,y-h,w,h,5,fill=1,stroke=1)
    c.setFillColor(accent);c.roundRect(x+8,y-h+10,3,h-20,1.5,fill=1,stroke=0)
    para(title,x+15,y-11,w-23,'node')
    if sub: para(sub,x+15,y-33,w-23,'node_small')

def diagram(kind,y):
    h=158 if kind not in ['pipeline','deployment','runtime'] else 180
    c.setFillColor(PALE);c.roundRect(M,y-h,CW,h,7,fill=1,stroke=0)
    x=M+14;top=y-13
    if kind=='pipeline':
        items=[('理解构想','目标 / 约束'),('编制规格','字段 / 检查'),('编排工具','动作 / 依赖'),('联动界面','表单 / 视图')]
        w=(CW-58)/4
        for i,(a,b) in enumerate(items):
            nx=x+i*(w+10);node(nx,top,w,60,a,b)
            if i<3:arrow(nx+w,top-30,nx+w+10,top-30)
        for i,(a,b) in enumerate([('检查发布','样例 / 权限 / 版本'),('执行留存','输入 / 回执 / 结果'),('复用演进','新材料 / 新规则')]):
            w2=(CW-48)/3;nx=x+i*(w2+10);node(nx,top-91,w2,61,a,b,TEAL)
            if i<2:arrow(nx+w2,top-122,nx+w2+10,top-122,TEAL)
        # Route from the fourth top node to the first bottom node.
        right_x=x+3*(w+10)+w/2;left_x=x+((CW-48)/3)/2
        c.setStrokeColor(BLUE);c.line(right_x,top-60,right_x,top-75)
        c.line(right_x,top-75,left_x,top-75)
        arrow(left_x,top-75,left_x,top-91)
    elif kind=='spec':
        labels=[('目标规格','目标 · 材料\n约束 · 未决项'),('动作规格','类型 · 工具\n权限 · 检查'),('应用清单','视图 · 工作流\n输入输出绑定')]
        w=(CW-52)/3
        for i,(a,b) in enumerate(labels):
            nx=x+i*(w+12);node(nx,top,w,83,a,b,BLUE if i!=1 else PURPLE)
            if i<2:arrow(nx+w,top-40,nx+w+12,top-40)
        para('结构解析 → 类型与引用核对 → 错误反馈 → 受约束修订',M+25,y-112,CW-50,'node_small')
    elif kind=='binding':
        w=142;node(x,top-28,w,82,'预算明细字段','资源引用 · 数值类型',BLUE)
        node(x+180,top,142,58,'求和与上限检查','动作参数 · 检查条件',PURPLE)
        node(x+180,top-77,142,58,'表单与预算视图','输入控件 · 输出路径',TEAL)
        arrow(x+w,top-65,x+180,top-29);arrow(x+w,top-65,x+180,top-106,TEAL)
        arrow(x+251,top-58,x+251,top-77,PURPLE)
        para('同一字段标识\n同一版本绑定',x+341,top-43,135,'node_small')
    elif kind=='extract':
        w=145;node(x,top-28,w,84,'来源任务轨迹','输入 · 动作 · 回执\n结果 · 检查',BLUE)
        node(x+177,top,134,59,'固定规则','稳定步骤 / 必要判断',PURPLE)
        node(x+177,top-77,134,59,'每次输入','替换旧文件依赖',TEAL)
        node(x+341,top-28,146,84,'新应用定义','适用范围 / 权限\n新输入检查',BLUE)
        arrow(x+w,top-63,x+177,top-28);arrow(x+w,top-63,x+177,top-106,TEAL)
        arrow(x+311,top-28,x+341,top-63);arrow(x+311,top-106,x+341,top-63,TEAL)
    elif kind=='runtime':
        w=(CW-58)/4
        for i,(a,b) in enumerate([('准备操作','身份 / 参数'),('派发动作','授权 / 工具'),('取得回执','效果 / 状态'),('核对成果','来源 / 版本')]):
            nx=x+i*(w+10);node(nx,top,w,67,a,b,BLUE)
            if i<3:arrow(nx+w,top-33,nx+w+10,top-33)
        node(x,top-94,224,59,'持久任务状态','中断、重启、重复请求与对账',PURPLE)
        node(x+250,top-94,237,59,'项目与应用边界','主体、材料、权限和预算',TEAL)
    elif kind=='evaluation':
        w=(CW-42)/2
        for i,(a,b) in enumerate([('实用性 40%','复用、修改与交接的实际价值'),('完整性 30%','目标到成果与复现材料闭合'),('技术难度 30%','统一规格、轨迹、依赖与执行'),('共同证据','固定条件、失败记录与对照')]):
            node(x+(i%2)*(w+14),top-(i//2)*70,w,60,a,b,[BLUE,TEAL,PURPLE,GRAY][i])
    elif kind=='deployment':
        node(x,top,150,63,'Windows工作台','C#宿主 / 现有前端',BLUE)
        node(x+178,top,140,63,'监督进程','生命周期与身份',PURPLE)
        node(x+347,top,140,63,'API + Worker','交互入口 / 独立执行',TEAL)
        arrow(x+150,top-31,x+178,top-31);arrow(x+318,top-31,x+347,top-31)
        node(x+40,top-94,185,61,'PostgreSQL','运行、成果与版本',TEAL)
        node(x+265,top-94,185,61,'书生模型 / 工具','受约束的规划与调用',PURPLE)
        arrow(x+417,top-64,x+357,top-94,PURPLE)
        c.setStrokeColor(TEAL);c.line(x+397,top-64,x+397,top-77)
        c.line(x+397,top-77,x+132,top-77)
        arrow(x+132,top-77,x+132,top-94,TEAL)
    return y-h-16

def table(data,y):
    headers,rs=data; n=len(headers)
    widths=([CW*.32,CW*.68] if n==2 else [CW*.24,CW*.36,CW*.40])
    cells=[[Paragraph(html.escape(s),styles['cellhead' if i==0 else 'cell']) for s in row] for i,row in enumerate([headers]+rs)]
    t=Table(cells,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8faff')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.6,LINE),('LINEBELOW',(0,-1),(-1,-1),.6,LINE)]))
    _,h=t.wrap(CW,1000);t.drawOn(c,M,y-h);return y-h-14

def cover(p):
    c.setFillColor(NAVY);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(colors.HexColor('#77d9f7'));c.setFont('CNB',10);c.drawString(M,H-48,'SIM2ACT / 方向3 · 开放赋能智能体')
    white=ParagraphStyle('cover',fontName='CNB',fontSize=31,leading=44,textColor=colors.white,wordWrap='CJK')
    q=Paragraph('让构想<br/>成为可用的应用',white);_,h=q.wrap(CW,200);q.drawOn(c,M,H-87-h)
    c.setFillColor(colors.HexColor('#b6cce7'));c.setFont('CN',12);c.drawString(M,H-213,'基于书生大模型的应用生成与演进平台')
    im=ImageReader(str(image_path(p['image'])));iw,ih=im.getSize();ph=CW*ih/iw
    c.drawImage(im,M,H-250-ph,width=CW,height=ph)
    yy=H-275-ph
    for head,body in p['sections']:
        q=Paragraph(html.escape(head),ParagraphStyle('ch',parent=styles['head'],textColor=colors.HexColor('#81d9ec')));_,h=q.wrap(CW,1000);q.drawOn(c,M,yy-h); yy-=h+6
        q=Paragraph(html.escape(body),ParagraphStyle('cb',parent=styles['body'],textColor=colors.HexColor('#dae6f6')));_,h=q.wrap(CW,1000);q.drawOn(c,M,yy-h);yy-=h+16
    c.setFont('CN',8);c.setFillColor(colors.HexColor('#a9bed9'));c.drawString(M,35,'技术创新赛参赛产品书 · 审阅版 v04 · 2026.11.07');c.drawRightString(W-M,35,'01 / 16')
    return yy

for number,p in enumerate(PAGES,1):
    if number==1: y=cover(p)
    else:
        y=header(number,p)
        if p.get('image'): y=screenshot(p['image'],y,240 if number==13 else 300)
        if p.get('diagram'): y=diagram(p['diagram'],y)
        if p.get('evidence_table'): y=table(p['evidence_table'],y)
        for heading,body in p['sections']:
            y=para(heading,M,y,CW,'head')-4
            y=para(body,M,y,CW,'body')-12
        if p.get('table'):y=table(p['table'],y)
        if p.get('references'):
            y=para('参考与入口',M,y,CW,'head')-7
            qr_top=y
            for label,url in p['references']:
                if number==16 and '/releases/tag/' in url: label='Release下载页 · v0.1.0-dev.20261107.1'
                text=f'<link href="{html.escape(url,quote=True)}" color="#255ce0">{html.escape(label)}</link>'
                pp=Paragraph(text,styles['small']);_,hh=pp.wrap(CW-155 if number==16 else CW,1000);pp.drawOn(c,M,y-hh);y-=hh+6
            if number==16:
                qr=ROOT/'submission/04_视频/生成图片/Sim2Act_Release_QR.png'
                c.drawImage(ImageReader(str(qr)),W-M-140,qr_top-140,140,140)
                c.linkURL('https://github.com/T1doo/Sim2Act/releases/tag/v0.1.0-dev.20261107.1',(W-M-140,qr_top-140,W-M,qr_top),relative=0)
                para('扫码查看下载页面',W-M-140,qr_top-148,140,'small')
        if p.get('caption'):y=para(p['caption'],M,y,CW,'small')-3
    layout.append(dict(page=number,title=p['title'],bottom=y))
    if y<50: raise ValueError(f'Page {number} exceeds content area: {y}')
    c.showPage()
c.save()

md=['---','title: Sim2Act 产品书','version: v04','date: 2026-11-07','status: 审阅稿','video_seconds: 270','---','','# Sim2Act：让构想成为可用的应用','','正文介绍完整正式设计，工程附录记录实际运行版本与验证范围。仓库、下载链接与体验步骤见第15–16页；介绍视频链接待成片后补入。','']
for i,p in enumerate(PAGES,1):
    md += [f'## 第{i}页 · {p["title"]}','',p['lead'],'']
    if p.get('image'):md += [f'![{p["title"]}]({image_path(p["image"]).relative_to(ROOT/"submission").as_posix().replace("04_视频/","../04_视频/").replace("03_图片与截图/","../03_图片与截图/")})','']
    if p.get('evidence_table'):
        heads,rs=p['evidence_table'];md+=['| '+' | '.join(heads)+' |','| '+' | '.join(['---']*len(heads))+' |']+['| '+' | '.join(r)+' |' for r in rs]+['']
    for head,body in p['sections']: md += [f'### {head}','',body,'']
    if p.get('table'):
        heads,rs=p['table'];md+=['| '+' | '.join(heads)+' |','| '+' | '.join(['---']*len(heads))+' |']+['| '+' | '.join(r)+' |' for r in rs]+['']
    if p.get('references'):md += [f'- [{label}]({url})' for label,url in p['references']]+['']
    md += [p['caption'],'']
(OUT/'Sim2Act_产品书_v04.md').write_text('\n'.join(md),encoding='utf-8')
(OUT/'产品书内容结构_v04.json').write_text(json.dumps(PAGES,ensure_ascii=False,indent=2),encoding='utf-8')
reader=PdfReader(str(PDF));assert len(reader.pages)==16
extracted=[page.extract_text() or '' for page in reader.pages]
for i,p in enumerate(PAGES): assert p['title'] in extracted[i].replace('\n','') or i==0
assert '17336' in extracted[12]
report=dict(pages=16,sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),layout=layout,text_extraction='PASS',visual_review='PENDING')
(OUT/'产品书排版检查_v04.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(pdf=str(PDF),pages=16,min_bottom=min(x['bottom'] for x in layout)),ensure_ascii=True))
