"""Deterministic film composition. Original graphics/audio; only validated app footage."""
import argparse, json, math, subprocess, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'demo'; WORK=D/'work'; FINAL=D/'final'; LOG=D/'logs'
for p in (WORK,FINAL,LOG):p.mkdir(exist_ok=True)
W,H=1920,1080
BG='#071a22'; WHITE='#f4fbff'; MUTE='#a1bcc7'; TEAL='#53e0c4'; BLUE='#75adff'
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
def label(draw,xy,text,size=30,fill=WHITE,bold=False):draw.text(xy,text,font=font(size,bold),fill=fill)
def centered(draw,y,text,size=60,fill=WHITE,bold=True):
    f=font(size,bold);box=draw.textbbox((0,0),text,font=f);draw.text(((W-box[2])/2,y),text,font=f,fill=fill)
def wrap(draw,text,size,width):
    words=text.split(); lines=[]; line=''
    for word in words:
        test=(line+' '+word).strip()
        if draw.textlength(test,font=font(size,True))>width and line:lines.append(line);line=word
        else:line=test
    return lines+[line]
def canvas():
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    for x in range(0,W,96):d.line((x,0,x,H),fill='#0b232c')
    for y in range(0,H,96):d.line((0,y,W,y),fill='#0b232c')
    d.rounded_rectangle((84,64,98,104),7,fill=TEAL)
    label(d,(120,64),'REVENUEGUARD AI',28,bold=True)
    label(d,(1410,68),'RAZORPAY BUILDATHON',21,fill=MUTE)
    return im,d
def card(e,summary,proof):
    im,d=canvas();kind=e['card']
    if kind in ('hook','problem','title','close'):
        if kind=='hook':
            label(d,(130,270),'01 / THE PROBLEM',24,TEAL,True)
            label(d,(130,354),"Failed payments",98,bold=True)
            label(d,(130,474),"aren't all the same.",98,TEAL,True)
            label(d,(135,660),e['detail'],36,MUTE)
        elif kind=='problem':
            label(d,(130,294),'RETRY ≠ RECOVERY',28,TEAL,True)
            label(d,(130,400),'Blind retries can',94,bold=True)
            label(d,(130,520),'make things worse.',94,bold=True)
            label(d,(135,700),e['detail'],36,MUTE)
        else:
            centered(d,280,'RevenueGuard AI',110)
            centered(d,448,e['detail'],39,TEAL,False)
            if kind=='close':
                centered(d,610,'Razorpay AI Buildathon 2026',34,MUTE,False)
                centered(d,668,'Track 03 — AI Revenue Recovery',32,MUTE,False)
            else:centered(d,620,'UNDERSTAND  →  RECOVER  →  PROTECT  →  MEASURE',29,MUTE)
    elif kind=='promise':
        label(d,(120,230),'RECOVERY, WITH JUDGMENT.',74,bold=True)
        rows=[('UNDERSTAND','ML probability + SHAP explanations + gateway health'),('PROTECT','Deterministic checks + high-value human approval'),('PROVE','Razorpay test mode + measurable recovery lift')]
        for i,(a,b) in enumerate(rows):
            y=394+i*142;label(d,(120,y),a,31,TEAL,True);label(d,(435,y-4),b,38)
        label(d,(120,897),'+9.9 pp offline recovery lift',44,TEAL,True)
        label(d,(850,909),'Held-out synthetic policy simulation; not production results.',27,MUTE)
    elif kind=='webhook':
        label(d,(120,194),'TRUST THE INTAKE',26,TEAL,True)
        label(d,(120,260),'Verify. Deduplicate. Activate.',74,bold=True)
        rows=[('invalid_signature_rejected','Invalid signature','REJECTED'),('valid_signature_accepted','Valid HMAC signature','ACCEPTED'),('duplicate_suppressed','Duplicate delivery','SUPPRESSED'),('exactly_one_case_created','Recovery case','CREATED ONCE')]
        for i,(k,a,b) in enumerate(rows):
            assert proof[k],f'No proof for {k}'
            y=386+i*111;d.rounded_rectangle((120,y,1800,y+86),14,fill='#102e38')
            label(d,(150,y+20),a,35);label(d,(1310,y+22),b,30,TEAL,True)
        label(d,(120,904),'Locally signed synthetic Razorpay-format replay',30,MUTE)
        label(d,(120,950),'Verified against the actual HTTP endpoint. Not a Razorpay-origin webhook.',25,MUTE)
    elif kind=='evaluation':
        ex=summary['experiment'];label(d,(120,182),'OFFLINE HELD-OUT EVALUATION',26,TEAL,True)
        label(d,(120,245),'Does it beat the baseline?',76,bold=True)
        for i,(name,rate,col,n) in enumerate([('Baseline',ex['control_rate'],BLUE,'151 / 401 recovered'),('Recovery policy',ex['variant_rate'],TEAL,'58 / 122 recovered')]):
            y=393+i*195;label(d,(125,y),name,35,bold=True);label(d,(1450,y),f'{rate*100:.1f}%',54,col,True)
            d.rounded_rectangle((125,y+72,125+int(rate/0.6*1370),y+115),12,fill=col)
            label(d,(125,y+125),n,27,MUTE)
        label(d,(125,837),f"{summary['total_events']} synthetic events",38,bold=True)
        label(d,(910,837),f"{summary['f1']*100:.1f}% ML F1",38,TEAL,True)
        label(d,(125,942),'Simulated recovery outcomes • committed evaluation artifacts',28,MUTE)
    elif kind=='lift':
        ex=summary['experiment'];label(d,(120,180),'OFFLINE POLICY SIMULATION',26,TEAL,True)
        centered(d,286,f"+{ex['absolute_lift']*100:.1f} pp",170,TEAL)
        centered(d,496,'absolute recovery lift',43)
        vals=[(220,f"+{ex['relative_lift']*100:.1f}%",'relative lift'),(805,f"p = {ex['p_value']:.3f}",'one-sided test'),(1390,'SRM passed','α = 0.01')]
        for x,big,small in vals:label(d,(x,665),big,47,bold=True);label(d,(x,732),small,28,MUTE)
        centered(d,864,'Measured. Reproducible. Auditable.',43)
        centered(d,960,'Synthetic outcomes—not production results or live LLM uplift.',26,MUTE,False)
    im.save(WORK/(e['scene']+'-card.png'));return WORK/(e['scene']+'-card.png')

def overlay(e):
    im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,47),fill=BG)
    label(d,(66,9),'REVENUEGUARD AI',21,WHITE,True)
    label(d,(1090,9),'LOCAL DEMO  /  SYNTHETIC PAYMENTS  /  NO REAL CHARGES',19,MUTE)
    d.rectangle((0,925,W,H),fill=BG)
    d.rectangle((66,954,73,1041),fill=TEAL)
    lines=wrap(d,e['caption'],43,1760)
    for i,line in enumerate(lines):label(d,(96,939+i*49),line,43,WHITE,True)
    detail_y=1000 if len(lines)==1 else 1041
    label(d,(96,detail_y),e.get('detail',''),27,MUTE)
    p=WORK/(e['scene']+'-overlay.png');im.save(p);return p

def focus_plate(e,cap):
    """Editorial magnification of an unmodified real screenshot, never a fake UI."""
    src=Image.open(ROOT/cap['screenshot']).convert('RGB');sx=src.width/1440
    b=cap.get('region')
    if not b:return None
    x,y,w,h=b['x'],b['y'],b['width'],b['height']
    crop=src.crop((max(0,int((x-7)*sx)),max(0,int((y-7)*sx)),min(src.width,int((x+w+7)*sx)),min(src.height,int((y+h+7)*sx))))
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    side=e['scene'] in ('gateway-defer','reasons','approved')
    maxw,maxh=(900,735) if side else (1650,760)
    ratio=min(maxw/crop.width,maxh/crop.height)
    crop=crop.resize((int(crop.width*ratio),int(crop.height*ratio)),Image.Resampling.LANCZOS)
    px=90 if side else (W-crop.width)//2;py=100+(760-crop.height)//2
    im.paste(crop,(px,py))
    if side:
        xx=1060
        if e['scene']=='gateway-defer':
            label(d,(xx,230),'RAIL-LEVEL INTELLIGENCE',25,TEAL,True)
            label(d,(xx,320),'OPEN → DEFER',61,bold=True)
            label(d,(xx,440),'A retry is not useful',40)
            label(d,(xx,497),'while the rail is failing.',40)
            label(d,(xx,624),'Wait. Reassess. Protect the customer.',29,MUTE)
        elif e['scene']=='reasons':
            label(d,(xx,175),'READ THE REASON CODES',26,TEAL,True)
            for j,(code,meaning) in enumerate([('RC03','Customer profile'),('RC05','Payment / error context'),('RC02','Failure / gateway features')]):
                yy=277+j*152;label(d,(xx,yy),code,40,TEAL,True);label(d,(xx,yy+57),meaning,31)
            label(d,(xx,789),'Feature groups—not causal guarantees.',26,MUTE)
        else:
            label(d,(xx,218),'PERSISTED + RESUMED',27,TEAL,True)
            label(d,(xx,318),'Approval recorded.',48,bold=True)
            label(d,(xx,420),'Worker resumed.',43)
            label(d,(xx,520),'Action: DEFER',54,TEAL,True)
            label(d,(xx,665),'Verified from the actual API / worker result.',26,MUTE)
    out=WORK/(e['scene']+'-focus.png');im.save(out);return out

def cmd(args,logname):
    with (LOG/logname).open('w',encoding='utf-8') as f:
        p=subprocess.run([str(a) for a in args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'Command failed; see demo/logs/{logname}')

def audio(events,duration):
    sr=48000;n=int(duration*sr);t=np.arange(n,dtype=np.float64)/sr
    music=np.zeros(n,dtype=np.float64)
    # Original restrained four-chord pad, generated mathematically; no samples.
    chords=[(130.8128,164.8138,195.9977),(110,130.8128,164.8138),(87.3071,110,130.8128),(97.9989,123.4708,146.8324)]
    for start in np.arange(0,duration,8):
        size=min(int(9*sr),n-int(start*sr));tt=np.arange(size)/sr
        env=np.minimum(tt/1.3,1)*np.minimum((size/sr-tt)/1.6,1)
        a=np.zeros(size)
        for freq in chords[int(start/8)%4]:a+=np.sin(2*np.pi*freq*tt)*.006+np.sin(2*np.pi*freq*2.002*tt)*.003
        music[int(start*sr):int(start*sr)+size]+=a*env
    music*=np.minimum(t/3,1)*np.minimum((duration-t)/4,1)
    rng=np.random.default_rng(37)
    def tick(at,level=.021):
        at=int(at*sr);size=min(int(.045*sr),n-at);tt=np.arange(size)/sr
        sound=(rng.normal(0,1,size)*.25+np.sin(2*np.pi*1850*tt)*.3)*np.exp(-tt*155)*level
        music[at:at+size]+=sound
    recorded=json.loads((LOG/'events.json').read_text())
    for e in events:
        if not e.get('sound_effect'):continue
        for event in recorded:
            if event.get('shot')!=e.get('source') or 'offset' not in event:continue
            at=e['timestamp']+event['offset']
            if event['type']=='click':tick(at)
            elif event['type']=='typing':
                for offset in (0,.16,.32):tick(at+offset,.012)
    stereo=np.column_stack((music,music*.98)).astype(np.float32)
    with wave.open(str(WORK/'original-score.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(stereo,-1,1)*32767).astype('<i2').tobytes())

def stamp(seconds):
    ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--draft',default='final');parser.add_argument('--cards-only',action='store_true');args=parser.parse_args()
    timeline=json.loads((D/'timeline.json').read_text(encoding='utf-8'));events=timeline['events']
    captures={x['id']:x for x in json.loads((LOG/'captures.json').read_text())}
    summary=json.loads((ROOT/'evals/results/summary.json').read_text());proof=json.loads((LOG/'webhook-proof.json').read_text())
    duration=sum(e['duration'] for e in events);parts=[]
    for i,e in enumerate(events):
        out=WORK/f'{args.draft}-{i:02}-{e["scene"]}.mp4';parts.append(out)
        if 'card' in e:
            asset=card(e,summary,proof)
            if args.cards_only:continue
            filters=f"scale=1960:1102,crop=1920:1080:x='20+12*sin(t/4)':y=11,fade=t=in:st=0:d=0.25,fade=t=out:st={e['duration']-.25}:d=0.25,format=yuv420p"
            command=['ffmpeg','-y','-loop','1','-framerate','30','-i',asset,'-vf',filters]
        else:
            cap=captures[e['source']];asset=overlay(e)
            if args.cards_only:continue
            focus=None if args.draft=='draft1' else (focus_plate(e,cap) if e['scene'] in ('gateway-defer','triage-focus','reasons','reasoning','policy','pending','approved') else None)
            # Actions keep their actual cursor timing; only validated final frames extend.
            if focus:
                vf=f"[0:v]scale=1958:1102,crop=1920:1080:x='19+8*sin(t/4)':y=11[v];[v][1:v]overlay=0:0,fade=t=in:st=0:d=0.22,fade=t=out:st={e['duration']-.22}:d=0.22,format=yuv420p[out]"
                command=['ffmpeg','-y','-loop','1','-framerate','30','-i',focus,'-i',asset,'-filter_complex',vf,'-map','[out]']
            else:
                vf=f"[0:v]fps=30,scale=1618:876:flags=lanczos,pad=1920:1080:151:48:color={BG.replace('#','0x')},tpad=stop_mode=clone:stop_duration={e['duration']},trim=duration={e['duration']},setpts=PTS-STARTPTS[v];[v][1:v]overlay=0:0,fade=t=in:st=0:d=0.18,fade=t=out:st={e['duration']-.18}:d=0.18,format=yuv420p[out]"
                command=['ffmpeg','-y','-ss',f"{cap['start']:.3f}",'-i',ROOT/cap['file'],'-i',asset,'-filter_complex',vf,'-map','[out]']
        command+=['-t',str(e['duration']),'-an','-c:v','libx264','-preset','fast','-crf','18','-r','30','-threads','4',out]
        cmd(command,'render-'+e['scene']+'.log');print('Rendered',e['scene'],flush=True)
    if args.cards_only:return
    concat=WORK/'concat.txt';concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts))
    video=WORK/(args.draft+'-picture.mp4')
    cmd(['ffmpeg','-y','-f','concat','-safe','0','-i',concat,'-c','copy',video],'concat.log')
    audio(events,duration)
    final=FINAL/'revenueguard-buildathon-demo.mp4' if args.draft=='final' else WORK/(args.draft+'.mp4')
    cmd(['ffmpeg','-y','-i',video,'-i',WORK/'original-score.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-af','loudnorm=I=-30:TP=-6:LRA=7','-ar','48000','-t',str(duration),'-movflags','+faststart',final],'mux.log')
    if args.draft=='final':
        cmd(['ffmpeg','-y','-i',video,'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-t',str(duration),'-movflags','+faststart',FINAL/'revenueguard-buildathon-demo-silent.mp4'],'silent-mux.log')
    srt='\n\n'.join(f"{i+1}\n{stamp(e['timestamp'])} --> {stamp(e['timestamp']+e['duration'])}\n{e['caption']}" for i,e in enumerate(events))+'\n'
    (FINAL/'revenueguard-buildathon-demo.srt').write_text(srt,encoding='utf-8')
    # Inspection contact sheet: middle frame of every scene.
    sheet=Image.new('RGB',(1280,math.ceil(len(events)/4)*210),BG);draw=ImageDraw.Draw(sheet)
    for i,e in enumerate(events):
        p=WORK/f'qa-{i:02}.jpg';cmd(['ffmpeg','-y','-ss',str(e['timestamp']+e['duration']/2),'-i',final,'-frames:v','1',p],'frame.log')
        thumb=Image.open(p).resize((320,180));x=i%4*320;y=i//4*210;sheet.paste(thumb,(x,y));draw.text((x+6,y+183),f"{stamp(e['timestamp'])[:8]} {e['scene']}",font=font(17),fill=WHITE)
    sheet.save(LOG/(args.draft+'-contact-sheet.jpg'))
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)]))
    (LOG/(args.draft+'-ffprobe.json')).write_text(json.dumps(probe,indent=2))
    if args.draft=='final':
        cmd(['ffmpeg','-y','-ss','232','-i',final,'-frames:v','1','-q:v','2',FINAL/'revenueguard-thumbnail.jpg'],'thumbnail.log')
    print('Film:',final,'duration:',duration,flush=True)

if __name__=='__main__':main()
