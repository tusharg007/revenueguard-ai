"""Verify signed local replay against the actual webhook route; no checkout claim."""
import hashlib
import hmac
import json
import os
import uuid
import httpx

def main():
    event_id='evt_demo_'+uuid.uuid4().hex
    body=json.dumps({'event':'payment.failed','event_id':event_id,'payload':{'payment':{'entity':{
        'id':'pay_demo_replay','amount':15000,'currency':'INR','method':'upi','bank':'SBI',
        'error_source':'bank','error_reason':'payment_failed','error_code':'GATEWAY_ERROR',
        'email':'','contact':'','notes':{'customer_name':'Demo customer','customer_id':'demo_replay'}
    }}}},separators=(',',':'))
    sig=hmac.new(os.environ['RAZORPAY_WEBHOOK_SECRET'].encode(),body.encode(),hashlib.sha256).hexdigest()
    with httpx.Client(timeout=30) as c:
        url='http://127.0.0.1:8010/webhooks/razorpay'
        headers={'X-Razorpay-Signature':sig,'x-razorpay-event-id':event_id,'Content-Type':'application/json'}
        before=c.get('http://127.0.0.1:8010/api/cases').json()['total']
        bad=c.post(url,content=body,headers={**headers,'X-Razorpay-Signature':'invalid'})
        first=c.post(url,content=body,headers=headers)
        duplicate=c.post(url,content=body,headers=headers)
        after=c.get('http://127.0.0.1:8010/api/cases').json()['total']
    result={'source':'locally signed synthetic Razorpay-format replay',
      'invalid_signature_rejected':bad.status_code==400,'valid_signature_accepted':first.status_code==200,
      'duplicate_suppressed':duplicate.json().get('status')=='duplicate',
      'exactly_one_case_created':after-before==1}
    assert all(v for k,v in result.items() if k!='source'),result
    from pathlib import Path
    Path('demo/logs/webhook-proof.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

if __name__=='__main__':main()
