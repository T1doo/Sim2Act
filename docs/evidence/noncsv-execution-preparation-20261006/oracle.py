"""Offline draft deterministic source/quote/completeness oracle, NOT product action.
Semantic obligation gold is developer-authored and still needs owner acceptance.
No inference, credentials, transport, database or file mutations in validate().
"""
import json

class Rejected(ValueError):
    pass

def reject_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise Rejected('duplicate key')
        result[key]=value
    return result

def parse(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>16000:raise Rejected('size/type')
    try:return json.loads(text,object_pairs_hook=reject_duplicates)
    except (ValueError,TypeError) as e:raise Rejected('invalid JSON') from e

def render(checklist):
    # Exact plain Markdown template; no generated HTML, images, scripts or links.
    source=checklist['source']
    rows=['# 来源约束清单',f"材料 {source['document_id']} / 版本 {source['document_version']}",f"SHA256 {source['document_sha256']}",f"原行 {source['line_start']}-{source['line_end']}",'']
    for rule in checklist['rules']:
        rows.extend([f"- [ ] {rule['rule_key']}（原行 {rule['line_start']}）",'  '+rule['quote'],'  必须覆盖：'+', '.join(rule['obligations'])])
    return '\n'.join(rows)+'\n'

def validate(value,contract):
    if not isinstance(value,dict) or set(value)!={'checklist','markdown'}:raise Rejected('envelope')
    checklist=value['checklist']
    if not isinstance(checklist,dict) or set(checklist)!={'contract_version','source','rules'}:raise Rejected('checklist shape')
    if type(checklist['contract_version']) is not int or checklist['contract_version']!=1:raise Rejected('contract version')
    if checklist['source']!=contract['gold']['source']:raise Rejected('source binding')
    # Type check integer fields explicitly: bool is not accepted as integer/version.
    if any(type(checklist['source'].get(k)) is not int for k in ['document_version','line_start','line_end']):raise Rejected('source integer type')
    rules=checklist['rules']
    if not isinstance(rules,list) or len(rules)!=4:raise Rejected('rule count')
    for actual,expected in zip(rules,contract['gold']['rules'],strict=True):
        if not isinstance(actual,dict) or set(actual)!={'rule_key','line_start','line_end','quote','obligations'}:raise Rejected('rule shape')
        if any(type(actual.get(k)) is not int for k in ['line_start','line_end']):raise Rejected('rule line type')
        if actual!=expected:raise Rejected('quote/span/obligation completeness')
    if not isinstance(value['markdown'],str) or value['markdown']!=render(checklist):raise Rejected('markdown differs from checked JSON')
    return True
