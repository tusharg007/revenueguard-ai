/* Open and seek both finished files in clean Chromium, independent of ffprobe. */
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
let chromium;try{({chromium}=require('playwright'));}catch{({chromium}=require('C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));}
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome',args:['--autoplay-policy=no-user-gesture-required']});const results=[];
 try{
  for(const name of ['revenueguard-buildathon-demo.mp4','revenueguard-buildathon-demo-silent.mp4']){
   const p=await browser.newPage();await p.goto(pathToFileURL(path.join(__dirname,'final',name)).href);
   await p.waitForFunction(()=>document.querySelector('video')?.readyState>=2);
   const meta=await p.evaluate(()=>{const v=document.querySelector('video');return {duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error?.code||null};});
   if(meta.width!==1920||meta.height!==1080||meta.error)throw Error('Browser media decode failed');
   await p.evaluate(()=>document.querySelector('video').play());await p.waitForTimeout(500);
   const playing=await p.evaluate(()=>document.querySelector('video').currentTime>0);if(!playing)throw Error('Playback did not advance');
   for(const at of [52,164,232]){await p.evaluate(at=>{document.querySelector('video').currentTime=at;},at);await p.waitForFunction(at=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-at)<2;},at);}
   results.push({file:name,...meta,playback_advanced:playing,seek_checks:'passed'});await p.close();
  }
 }finally{await browser.close();}
 fs.writeFileSync(path.join(__dirname,'logs','browser-playback.json'),JSON.stringify(results,null,2));console.log('Both exports opened, played and sought successfully in Chromium.');
})().catch(e=>{console.error(e.message);process.exit(1);});
