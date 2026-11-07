from pathlib import Path
from decimal import Decimal
import json
BASE=Path(__file__).resolve().parent
def evaluate(amounts,unit,normalize,permission_changed=False):
    if permission_changed:raise ValueError('PERMISSION_SCOPE_CHANGED')
    if unit not in {'CNY','CNY_10000'}:raise ValueError('UNIT_REQUIRED')
    if unit!='CNY' and not normalize:raise ValueError('UNIT_MISMATCH')
    factor=Decimal(10000) if unit=='CNY_10000' else Decimal(1)
    values=[Decimal(x)*factor for x in amounts]
    if not all(x.is_finite() for x in values):raise ValueError('NON_FINITE_AMOUNT')
    return values,sum(values,Decimal(0))
def rule_gate(current,incoming):
    if incoming is None:return 'WAIT_FOR_CONFIRMATION'
    return 'REUSE_CURRENT_VERSION' if current==incoming else 'BLOCK_REUSE_AND_ENTER_T3'
if __name__=='__main__':
    spec=json.loads((BASE/'业务样例规范_v02.json').read_text(encoding='utf-8'))
    example=spec['unit_repair'];values,total=evaluate(example['source_amounts'],example['source_unit'],True)
    assert values==[Decimal(x) for x in example['normalized_amounts']]
    assert total==Decimal(example['expected_total'])
    assert Decimal(example['budget_limit'])-total==Decimal(example['expected_remaining'])
    bad=[]
    for label,unit,normal,escalate in [('缺失单位',None,True,False),('漏做换算','CNY_10000',False,False),('扩大权限','CNY_10000',True,True)]:
        try:evaluate(example['source_amounts'],unit,normal,escalate)
        except ValueError as e:bad.append({'case':label,'diagnostic':str(e)})
        else:raise AssertionError(label)
    assert rule_gate('r1','r2')=='BLOCK_REUSE_AND_ENTER_T3'
    assert rule_gate('r1',None)=='WAIT_FOR_CONFIRMATION'
    report={'status':'DESIGN_EXAMPLE_CHECKED_NOT_PRODUCT_ACCEPTANCE','total':str(total),'remaining':str(Decimal(example['budget_limit'])-total),'rejected':bad,'new_rule':'BLOCK_REUSE_AND_ENTER_T3','unknown_rule':'WAIT_FOR_CONFIRMATION','qualification':'证据不足，人工确认待处理','live_model_calls':0}
    (BASE/'业务样例校验_v02.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
