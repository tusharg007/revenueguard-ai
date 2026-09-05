"""Validate both deliverables, proof gates and caption timing; fully decode MP4s."""
import json, subprocess, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'demo';L=D/'logs';F=D/'final'
events=json.loads((D/'timeline.json').read_text(encoding='utf-8'))['events']
position=0
for e in events:
    assert e['timestamp']==position,(e['scene'],position)
    position+=e['duration']
assert 210<=position<=260
proof=json.loads((L/'webhook-proof.json').read_text())
assert all(v for k,v in proof.items() if k!='source')
assert json.loads((L/'approval-proof.json').read_text())['approved']
assert json.loads((L/'razorpay-proof.json').read_text())['test_mode']
report={'duration_seconds':position,'webhook_checks':proof,'files':[]}
for name in ['revenueguard-buildathon-demo.mp4','revenueguard-buildathon-demo-silent.mp4']:
    p=F/name
    raw=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
    v=next(x for x in raw['streams'] if x['codec_type']=='video');a=next(x for x in raw['streams'] if x['codec_type']=='audio')
    assert v['codec_name']=='h264' and v['width']==1920 and v['height']==1080
    assert a['codec_name']=='aac' and v['pix_fmt']=='yuv420p'
    n,d=map(int,v['avg_frame_rate'].split('/'));assert n/d>=30
    assert abs(float(raw['format']['duration'])-position)<.15
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode==0 and not decoded.stderr.strip(),decoded.stderr
    meter=subprocess.run(['ffmpeg','-hide_banner','-i',str(p),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True)
    (L/(p.stem+'-audio.txt')).write_text(meter.stderr[-1200:])
    report['files'].append({'file':name,'codec':v['codec_name'],'audio':a['codec_name'],'width':v['width'],'height':v['height'],'fps':n/d,'duration':float(raw['format']['duration']),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'full_decode':'passed'})
    print('Validated',name,flush=True)
(L/'validation.json').write_text(json.dumps(report,indent=2))
