from common import *
results=[]
for case in ['joint-promotion','joint-downgrade']:
 folder=ROOT/('api-'+case);url='sqlite:///'+str(folder/'db.sqlite');store=Store(url,test_only=True);settings=Settings(url,folder,mode='mock');client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer review-A';e=[store,settings,client,None,None,None,None]
 with store.engine.connect() as c:a=c.execute(select(internal_approvals)).mappings().one()
 before=fingerprint(snapshot(e));response=client.post('/api/internal/approvals/'+a['id']+'/commit',json={'fingerprint':a['fingerprint']});after=fingerprint(snapshot(e));out={'case':case,'status':response.status_code,'body':response.json(),'zero_allDB_writes':before==after};assert response.status_code==409 and 'actual source receipts' in response.json()['error']['message'] and before==after;results.append(out);client.close();store.engine.dispose()
(ROOT/'joint-version-denial-reasons.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
