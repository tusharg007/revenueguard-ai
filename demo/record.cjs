/* Genuine browser actions against the isolated application. No API response mocking. */
const fs=require('fs'), path=require('path'), cp=require('child_process');
let chromium;
try { ({chromium}=require('playwright')); }
catch { ({chromium}=require('C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')); }
const root=path.resolve(__dirname,'..'), raw=path.join(__dirname,'raw'), logs=path.join(__dirname,'logs');
const base='http://127.0.0.1:3010', api='http://127.0.0.1:8010';
const shots=[], events=[];let activeShot=null,activeStart=0;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function request(route,method='GET',data){
 const res=await fetch(api+route,{method,headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(180000)});
 if(!res.ok)throw Error(`${route}: HTTP ${res.status}`);return res.json();
}
async function pointer(page,target,click=false){
 const box=await target.boundingBox();if(!box)throw Error('Missing cursor target');
 const end={x:box.x+box.width/2,y:box.y+box.height/2};
 const start=await page.evaluate(()=>window.__pos||{x:180,y:680});
 for(let i=1;i<=42;i++){
  const t=i/42,e=t*t*(3-2*t);const x=start.x+(end.x-start.x)*e,y=start.y+(end.y-start.y)*e-25*Math.sin(Math.PI*t);
  await page.mouse.move(x,y);await page.evaluate(({x,y})=>{const el=document.querySelector('#film-pointer');el.style.left=x+'px';el.style.top=y+'px';window.__pos={x,y};},{x,y});await pause(15);
 }
 await pause(330);
 if(click){events.push({shot:activeShot,type:'click',offset:(Date.now()-activeStart)/1000});await target.click();await page.evaluate(()=>{const el=document.querySelector('#film-pointer');el.animate([{filter:'drop-shadow(0 0 0 #14b8a6)'},{filter:'drop-shadow(0 0 8px #14b8a6)'},{filter:'drop-shadow(0 0 0 #14b8a6)'}],{duration:350});});}
}
async function scrollTo(page,target){
 const b=await target.boundingBox();if(!b)return;
 await page.evaluate(y=>window.scrollBy({top:y-95,behavior:'smooth'}),b.y);await pause(1100);
}
async function decorate(page){
 await page.addStyleTag({content:'nextjs-portal{display:none!important}body{scroll-behavior:smooth}'});
 await page.evaluate(()=>{
   const c=document.createElement('div');c.id='film-pointer';c.style.cssText='position:fixed;left:180px;top:680px;z-index:2147483647;pointer-events:none;width:22px;height:28px;filter:drop-shadow(0 2px 3px #0008)';
   c.innerHTML='<svg viewBox="0 0 24 30"><path d="M2 1L21 18L12 19L8 27Z" fill="white" stroke="#083c38" stroke-width="1.6"/></svg>';document.body.append(c);
 });
}
async function capture(browser,id,route,ready,action,opts={}){
 const ctx=await browser.newContext({viewport:{width:1440,height:780},deviceScaleFactor:2,recordVideo:{dir:raw,size:{width:1440,height:780}},colorScheme:'light',locale:'en-IN'});
 const p=await ctx.newPage();p.setDefaultTimeout(30000);
 p.on('pageerror',e=>events.push({shot:id,type:'pageerror',message:e.message.slice(0,180)}));
 try{
  await p.goto(base+route,{waitUntil:'networkidle',timeout:90000});
  await ready(p);await pause(800);await decorate(p);
  if(opts.prepare)await opts.prepare(p);
  const start=Date.now();activeShot=id;activeStart=start;await pause(700);
  if(action)await action(p);
  await pause(1800);
  const regionTargets={gateway:['card',p.getByRole('heading',{name:'SBI',exact:true})],triage:['card',p.getByRole('heading',{name:'ML triage',exact:true})],reasons:['card',p.getByRole('heading',{name:'ML triage',exact:true})],reasoning:['trace',p.getByText('Agent Diagnose',{exact:true}).last()],policy:['trace',p.getByText('Policy Check',{exact:true}).last()],pending:['card',p.getByRole('heading',{name:'Approval Required'})],approved:['card',p.getByRole('heading',{name:'Approval history'})]};
  let region=null;
  if(regionTargets[id]){const [kind,target]=regionTargets[id];region=await target.evaluate((el,kind)=>{const node=kind==='card'?el.closest('section'):el.closest('div.rounded-md');const b=node.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};},kind);}
  await p.screenshot({path:path.join(raw,id+'.png')});
  const active=(Date.now()-start)/1000;
  const video=p.video();await ctx.close();const file=await video.path();
  const duration=Number(cp.execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',file],{encoding:'utf8'}));
  shots.push({id,route,file:path.relative(root,file).replaceAll('\\','/'),start:Math.max(0,duration-active),duration:active,screenshot:'demo/raw/'+id+'.png',region});
  fs.writeFileSync(path.join(logs,'captures.json'),JSON.stringify(shots,null,2));console.log('Captured '+id);
 }catch(e){await p.screenshot({path:path.join(logs,'diagnostic-'+id+'.png')}).catch(()=>{});await ctx.close();throw e;}
}
async function waitCases(){
 for(let i=0;i<100;i++){
  const c=await request('/api/cases?page_size=100');
  if(c.items.every(x=>!['detected','triaging'].includes(x.status)))return c;
  await pause(1500);
 }
 throw Error('Worker did not finish in time; no fabricated processing state');
}
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const readyDash=p=>p.getByRole('button',{name:'Run Recovery Batch'}).waitFor();
 try{
  // Reference is viewed only; no asset or audio extraction.
  const ref=await browser.newPage();
  try{await ref.goto('https://www.youtube.com/watch?v=1jEiY4bB3lw',{waitUntil:'domcontentloaded',timeout:20000});fs.writeFileSync(path.join(logs,'reference.json'),JSON.stringify({title:await ref.title(),usage:'presentation inspiration only; no assets copied'}));}catch{fs.writeFileSync(path.join(logs,'reference.json'),JSON.stringify({status:'reference unavailable',usage:'user-specified restrained product-film style'}));}await ref.close();
  await capture(browser,'overview','/',readyDash,async p=>{await pointer(p,p.getByText('Revenue at Risk',{exact:true}));await pause(1200);await pointer(p,p.getByText('Active Failed Payments',{exact:true}));});
  await capture(browser,'batch','/',readyDash,async p=>{
   await pointer(p,p.getByRole('button',{name:'Run Recovery Batch'}),true);
   await p.waitForResponse(r=>r.url().includes('/api/metrics')&&r.status()===200);await pause(1300);
  },{prepare:async p=>{await scrollTo(p,p.getByRole('button',{name:'Run Recovery Batch'}));}});
  const cases=await waitCases();fs.writeFileSync(path.join(logs,'batch-summary.json'),JSON.stringify({total:cases.total,statuses:cases.items.reduce((o,x)=>(o[x.status]=(o[x.status]||0)+1,o),{})},null,2));
  await capture(browser,'populated','/',async p=>{await readyDash(p);await p.getByText('50',{exact:true}).first().waitFor();},async p=>{await pointer(p,p.getByText('Revenue at Risk',{exact:true}));});
  await capture(browser,'outage','/',readyDash,async p=>{
   const response=p.waitForResponse(r=>r.url().includes('/api/simulate/outage')&&r.status()===200);
   await pointer(p,p.getByRole('button',{name:'Simulate SBI Outage'}),true);const r=await response;
   fs.writeFileSync(path.join(logs,'outage-proof.json'),JSON.stringify(await r.json(),null,2));
  },{prepare:async p=>{await scrollTo(p,p.getByRole('button',{name:'Simulate SBI Outage'}));}});
  await capture(browser,'gateway','/gateway-health',p=>p.getByText('DEFER',{exact:true}).waitFor(),async p=>{
    await pointer(p,p.getByRole('heading',{name:'SBI',exact:true}));await pause(1000);await pointer(p,p.getByText('DEFER',{exact:true}));
  });
  const ids=await request('/demo/scenarios','POST');fs.writeFileSync(path.join(logs,'scenario-ids.json'),JSON.stringify(ids,null,2));
  const hero=await request('/api/cases/'+ids.hero),high=await request('/api/cases/'+ids.approval);
  if(hero.case.status==='failed'||!hero.audit_trail.some(a=>a.step==='agent_diagnose'))throw Error('Actual LLM case failed; review diagnostics');
  if(!high.approvals.some(a=>a.status==='PENDING'))throw Error('Actual high-value policy did not create pending approval');
  fs.writeFileSync(path.join(logs,'scenario-proof.json'),JSON.stringify({hero:{probability:hero.triage.recovery_probability,reasons:hero.triage.shap_reason_codes,action:hero.actions.map(a=>a.action_type),steps:hero.audit_trail.map(a=>a.step)},approval:{amount:high.case.amount_paise,status:high.approvals[0].status,actions_before:high.actions.length}},null,2));
  const caseReady=p=>p.getByRole('heading',{name:'ML triage',exact:true}).waitFor();
  await capture(browser,'triage','/cases/'+ids.hero,caseReady,async p=>{await pointer(p,p.getByRole('heading',{name:'ML triage',exact:true}));});
  await capture(browser,'reasons','/cases/'+ids.hero,caseReady,async p=>{await pointer(p,p.getByText(hero.triage.shap_reason_codes[0],{exact:true}).first());});
  await capture(browser,'timeline','/cases/'+ids.hero,caseReady,async p=>{await pointer(p,p.getByRole('heading',{name:'Decision timeline',exact:true}));});
  await capture(browser,'reasoning','/cases/'+ids.hero,caseReady,async p=>{
   const t=p.getByText('Agent Diagnose',{exact:true}).last();await scrollTo(p,t);await pointer(p,t);
  },{prepare:async p=>{await scrollTo(p,p.getByRole('heading',{name:'Agent trace',exact:true}));}});
  await capture(browser,'policy','/cases/'+ids.hero,caseReady,async p=>{const t=p.getByText('Policy Check',{exact:true}).last();await pointer(p,t);},{prepare:async p=>{await scrollTo(p,p.getByText('Policy Check',{exact:true}).last());}});
  await capture(browser,'pending','/cases/'+ids.approval,p=>p.getByRole('heading',{name:'Approval Required'}).waitFor(),async p=>{await pointer(p,p.getByRole('button',{name:'Approve',exact:true}));},{prepare:async p=>{await scrollTo(p,p.getByRole('heading',{name:'Approval Required'}));}});
  await capture(browser,'approve','/cases/'+ids.approval,p=>p.getByRole('button',{name:'Approve',exact:true}).waitFor(),async p=>{
   await pointer(p,p.getByRole('button',{name:'Approve',exact:true}),true);await p.getByRole('heading',{name:'Approval history'}).waitFor();
  },{prepare:async p=>{await scrollTo(p,p.getByRole('heading',{name:'Approval Required'}));}});
  await waitCases();const after=await request('/api/cases/'+ids.approval);
  if(!after.approvals.some(a=>a.status==='APPROVED')||!after.actions.length)throw Error('Approval did not persist and resume');
  fs.writeFileSync(path.join(logs,'approval-proof.json'),JSON.stringify({approved:true,action:after.actions.map(a=>({type:a.action_type,status:a.status})),source:'actual dashboard approval endpoint and worker'},null,2));
  await capture(browser,'approved','/cases/'+ids.approval,p=>p.getByRole('heading',{name:'Approval history'}).waitFor(),async p=>{await pointer(p,p.getByRole('heading',{name:'Approval history'}));},{prepare:async p=>{await scrollTo(p,p.getByRole('heading',{name:'Approval history'}));}});
  await capture(browser,'sandbox','/sandbox',p=>p.getByText('Razorpay connected',{exact:true}).waitFor(),async p=>{
    await pointer(p,p.getByLabel('Amount (INR)'),true);await p.getByLabel('Amount (INR)').fill('');events.push({shot:'sandbox',type:'typing',offset:(Date.now()-activeStart)/1000});await p.getByLabel('Amount (INR)').pressSequentially('500',{delay:160});
    const response=p.waitForResponse(r=>r.url().endsWith('/api/orders')&&r.request().method()==='POST');
    await pointer(p,p.getByRole('button',{name:'Create Razorpay Order'}),true);const r=await response;
    const data=await r.json();if(r.status()!==200||!data.order_id)throw Error('Real test order failed');
    fs.writeFileSync(path.join(logs,'razorpay-proof.json'),JSON.stringify({test_mode:true,order_created:true,amount:data.amount,currency:data.currency,no_charge_created:true}));
  });
  cp.execFileSync(path.join(root,'.venv/Scripts/python.exe'),['-m','demo.proof'],{env:process.env,stdio:'inherit'});
  await capture(browser,'experiments','/experiments',p=>p.getByText('Experiment sample',{exact:true}).waitFor(),async p=>{await pointer(p,p.getByRole('heading',{name:'Recovery rate comparison'}));});
  await capture(browser,'closing','/',readyDash,async p=>{await pointer(p,p.getByText('Revenue at Risk',{exact:true}));});
 } finally {fs.writeFileSync(path.join(logs,'events.json'),JSON.stringify(events,null,2));await browser.close();}
})().catch(e=>{console.error(e.message);fs.writeFileSync(path.join(logs,'recording-error.json'),JSON.stringify({message:e.message}));process.exit(1);});
