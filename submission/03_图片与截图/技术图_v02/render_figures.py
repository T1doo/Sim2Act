from pathlib import Path
import json, html, hashlib
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

root=Path(__file__).resolve().parents[3]
out=root/'submission/03_图片与截图/技术图_v02';out.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc'))
pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc'))
W,H=1920,1080;navy='#152945';blue='#285ee2';purple='#775be8';teal='#008e9a';amber='#b66a13'
c=canvas.Canvas(str(out/'Sim2Act_技术架构与四项机制_v02.pdf'),pagesize=(W,H),pageCompression=1)
c.setTitle('Sim2Act 技术机制主图')
def text(s,x,y,w,size=32,bold=False,color=navy,center=False):
    p=Paragraph(html.escape(s).replace('\n','<br/>'),ParagraphStyle('p',fontName='CNB' if bold else 'CN',fontSize=size,leading=size*1.5,textColor=colors.HexColor(color),wordWrap='CJK',alignment=1 if center else 0));_,h=p.wrap(w,1000);p.drawOn(c,x,H-y-h)
def box(x,y,w,h,title,body,accent=blue):
    c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#c9d7ec'));c.setLineWidth(2);c.roundRect(x,H-y-h,w,h,18,fill=1,stroke=1)
    c.setFillColor(colors.HexColor(accent));c.roundRect(x+20,H-y-h+20,6,h-40,3,fill=1,stroke=0)
    text(title,x+44,y+23,w-65,34,True);text(body,x+44,y+82,w-65,27,color='#52667f')
def arrow(points,label='',labelxy=None,color=blue,dashed=False):
    import math
    c.setStrokeColor(colors.HexColor(color));c.setFillColor(colors.HexColor(color));c.setLineWidth(3)
    c.setDash(9,5) if dashed else c.setDash()
    for (x1,y1),(x2,y2) in zip(points,points[1:]):c.line(x1,H-y1,x2,H-y2)
    c.setDash();(x1,y1),(x2,y2)=points[-2:];a=math.atan2(y2-y1,x2-x1)
    p=c.beginPath();p.moveTo(x2,H-y2);p.lineTo(x2-13*math.cos(a-.5),H-(y2-13*math.sin(a-.5)));p.lineTo(x2-13*math.cos(a+.5),H-(y2-13*math.sin(a+.5)));p.close();c.drawPath(p,fill=1,stroke=0)
    if label and labelxy:
        x,y,w=labelxy;c.setFillColor(colors.HexColor('#f0f5fd'));c.roundRect(x-7,H-y-45,w+14,50,6,fill=1,stroke=0);text(label,x,y,w,25,color=color,center=True)
def start(num,title,sub):
    c.setFillColor(colors.HexColor('#f0f5fd'));c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(colors.HexColor(blue));c.rect(0,H-10,W*.6,10,fill=1,stroke=0);c.setFillColor(colors.HexColor(purple));c.rect(W*.6,H-10,W*.4,10,fill=1,stroke=0)
    text('Sim2Act / TECHNICAL DESIGN',80,35,1500,26,True,blue)
    text(title,80,95,1760,57,True);text(sub,80,182,1760,29,color='#52667f')
    text(f'{num:02d} / 05',1710,1015,130,22,color='#52667f',center=True)

start(1,'ARCH-01 · 两条入口，同一应用对象','从目标创建，或从独立任务提取；统一规格同时约束界面、执行与检查。')
box(80,300,460,190,'P-A：目标与材料','目标、输入范围、约束\n未决条件与交付要求')
box(80,660,460,220,'P-B：独立任务轨迹','来源任务、回执与结果\n稳定步骤、变量与适用范围',purple)
box(750,430,450,280,'统一应用规格','GoalSpec / ActionSpec\nAppManifest\n版本、来源与权限',purple)
box(1410,260,430,180,'专用界面','字段 → 表单\n动作 → 按钮')
box(1410,540,430,180,'工具执行','类型参数、预算与授权\n操作身份和回执',teal)
box(1410,820,430,160,'独立检查','结构、数值、引用\n语义与人工接受分别记录',amber)
arrow([(540,395),(750,510)],'书生规划',(545,420,190))
arrow([(540,770),(750,640)],'提取与参数化',(545,690,195),purple)
arrow([(1200,480),(1300,480),(1300,350),(1410,350)],'视图绑定',(1220,300,180))
arrow([(1200,575),(1410,630)],'动作绑定',(1215,535,180),teal)
arrow([(1200,675),(1300,675),(1300,900),(1410,900)],'检查绑定',(1210,740,180),amber)
text('工具回执与检查反馈进入受约束修订；发布、运行、结果和规则分别保存版本。',80,950,1160,27,True,navy)
c.showPage()

start(2,'T1-01 · 字段、单位与结果绑定','budget_items[].amount → 单位标准化 → sum_budget → budget_total:CNY')
box(80,290,510,220,'预算明细输入','设备4 / 材料3.5 / 服务1.5\n来源单位：CNY_10000（万元）\nbudget_items[].amount')
box(705,290,510,220,'单位标准化','normalize_amount\nCNY_10000 → CNY\n40000 / 35000 / 15000',teal)
box(1330,290,510,220,'可信求和动作','sum_budget\n输出 budget_total:CNY\n¥90,000',teal)
arrow([(590,400),(705,400)],'换算',(600,350,95))
arrow([(1215,400),(1330,400)],'传参',(1225,350,95),teal)
box(80,720,510,220,'错误候选：直接传入','万元值未转换为元\nUNIT_MISMATCH\n执行被阻止',amber)
box(705,720,510,220,'定位并受限修订','返回字段位置与单位要求\n补充确定性换算动作\n权限与验收条件保持',purple)
box(1330,720,510,220,'输出同时绑定视图与检查','view.total ← budget_total\nbudget_limit_check ← 总额、上限\n¥100,000 − ¥90,000 = ¥10,000')
arrow([(590,820),(705,820)],'反馈',(600,770,95),amber)
arrow([(960,720),(960,510)],'修订候选',(855,585,210),purple)
arrow([(1585,510),(1585,720)],'输出绑定',(1470,585,230),teal)
c.showPage()

start(3,'T2-01 · 从一次任务到独立新运行','保存来源用于追溯；新执行只接收明确的新输入，不静默使用旧文件内容。')
box(80,410,430,250,'独立一次性任务','没有既存应用作为来源\n目标、调用、回执、结果\n明确未观察分支边界')
box(715,280,480,200,'固定规则与方法','必要步骤、检查与判断\n工具版本、权限与适用范围',purple)
box(715,650,480,200,'可变输入','新指南、新团队资料、新附件\n解除旧路径与旧内容绑定',teal)
box(1400,300,440,250,'复用检查门','新输入 / 错误输入 / 冷会话\n旧材料不进入新推理上下文\n新指南规则兼容性',amber)
box(1400,730,440,190,'确认应用后另行运行','明确确认范围并发布\n新运行产生独立成果')
arrow([(510,470),(715,380)],'步骤提取',(520,370,185),purple)
arrow([(510,600),(715,750)],'变量识别',(520,675,185),teal)
arrow([(1195,380),(1400,425)],'必要约束',(1205,325,185),purple)
arrow([(1195,750),(1290,750),(1290,500),(1400,500)],'新资料',(1200,565,180),teal)
arrow([(1620,550),(1620,730)],'检查后确认',(1490,620,260))
text('指南规则改变 → 阻止沿用旧版本，进入T3；规则无法确定 → 等待人工确认。',80,960,1750,29,True,navy)
c.showPage()

start(4,'T3-01 · 先隔离预验，再确认发布与新运行','预算明细保持90000；上限从100000变为80000，预验应显示超限10000。')
box(80,300,440,190,'新规则与来源','指南 r1 → r2\n上限 ¥100,000 → ¥80,000',purple)
box(740,300,440,190,'影响分析','类型依赖 + 实际读取\n未知依赖扩大重验范围',purple)
box(1400,300,440,190,'隔离预验','规则、检查、提示应变\n不写入正式结果历史',teal)
box(80,700,440,190,'锁定或不确定冲突','需人工确认\n不静默覆盖',amber)
box(740,700,440,190,'保留集合','团队资料、已确认附件\n旧运行与原规则归属',teal)
box(1400,700,440,190,'用户确认发布 v2','已发布 ≠ 已运行\n新输入与运行另行确认')
arrow([(520,395),(740,395)],'规则差异',(545,340,170),purple)
arrow([(1180,395),(1400,395)],'应变集合',(1208,340,175),purple)
arrow([(740,450),(630,450),(630,600),(300,600),(300,700)],'冲突分支',(340,545,250),amber)
arrow([(960,490),(960,700)],'应保持集合',(835,570,250),teal)
arrow([(1620,490),(1620,700)],'通过预验后确认',(1450,570,340))
arrow([(1180,795),(1400,795)],'保留归属',(1206,740,180),teal)
text('发布后：用户点击按v2运行 → 新结果编号3；旧结果编号1仍对应应用v1 / 规则r1。',80,970,1750,28,True,navy)
c.showPage()

start(5,'T4-01 · 回执未知时，先核对原操作','超时或响应丢失不等于失败，也不等于成功；核对结果决定后续处理。')
box(80,290,500,190,'准备操作','PREPARED\n绑定身份、参数、授权与预算')
box(710,290,500,190,'派发原操作','DISPATCHED\n稳定operation_id与请求键',purple)
box(1340,290,500,190,'响应未确认','OUTCOME_UNKNOWN\n保留原身份，不盲目重发',amber)
arrow([(580,385),(710,385)],'派发',(590,330,110))
arrow([(1210,385),(1340,385)],'响应丢失',(1210,330,130),amber)
box(710,610,500,150,'按原操作身份核对','重新检查权限与效果来源',purple)
arrow([(1590,480),(1590,555),(960,555),(960,610)],'查询原操作',(1110,500,260),amber)
box(80,810,500,160,'查明已提交','回读原回执与成果\n不再重复派发',teal)
box(1340,810,500,160,'权威确认没有效果','安全失败或重新确认\n不能仅凭查无记录下结论',teal)
box(710,875,500,130,'仍然未知','保持未知，转人工核对',amber)
arrow([(710,680),(620,680),(620,890),(580,890)],'已找到',(390,715,230),teal)
arrow([(1210,680),(1300,680),(1300,890),(1340,890)],'有无效果依据',(1280,715,270),teal)
arrow([(960,760),(960,875)],'仍不确定',(840,790,240),amber)
c.showPage();c.save()
mapping=[{'id':'ARCH-01','page':1,'purpose':'两条入口与统一应用规格'},{'id':'T1-01','page':2,'purpose':'单位错误拒绝与字段输出绑定'},{'id':'T2-01','page':3,'purpose':'轨迹提取、新输入与规则兼容'},{'id':'T3-01','page':4,'purpose':'隔离预验、发布和新运行'},{'id':'T4-01','page':5,'purpose':'未知回执核对与副作用边界'}]
(out/'图号映射.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')

# Actual story PDFs support the pictured source location; they are not live app evidence.
from reportlab.lib.pagesizes import A4
sample_dir=root/'submission/03_图片与截图/业务样例';sample_dir.mkdir(exist_ok=True)
for version,limit in [('v1','100000'),('v2','80000')]:
    doc=canvas.Canvas(str(sample_dir/f'申报指南_{version}.pdf'),pagesize=A4)
    doc.setTitle(f'星桥研究团队申报材料规范 {version}');doc.setAuthor('Sim2Act story materials')
    for pg in [1,2]:
        doc.setFont('CNB',19);doc.drawString(48,780,'星桥研究团队 · 申报材料规范')
        doc.setFont('CN',11);doc.drawString(48,750,f'文件版本：{version} / 指南规则：r{version[-1]}')
        lines=([('1. 材料与预算','提供申报材料、预算明细、团队资料与附件清单。'),('1.1 金额单位','预算明细须明确标注元或万元。单位不明时应先补充说明。'),('1.2 预算上限',f'本版预算上限为人民币{limit}元。')]
               if pg==1 else [('2. 资格与证据','资格判断依据申报指南及团队提供的证明材料。'),('2.1 在岗要求','项目负责人须为本单位在岗人员，并提供在岗证明。'),('2.2 人工确认','缺少证明时保持证据不足，由负责人补充或确认。'),('2.3 附件检查','检查附件的存在性与格式，不替代签字真实性或业务资格判断。'),('2.4 签字页','申请材料须包含团队负责人签字页。')])
        y=695
        for title,body in lines:
            doc.setFont('CNB',13);doc.drawString(48,y,title);y-=30
            p=Paragraph(body,ParagraphStyle('body',fontName='CN',fontSize=12,leading=21,wordWrap='CJK'));_,hh=p.wrap(495,100);p.drawOn(doc,48,y-hh);y-=hh+42
        doc.setFont('CN',10);doc.drawRightString(545,35,f'{pg} / 2');doc.showPage()
    doc.save()
print('Five technical pages and two source-guideline PDFs rendered')
