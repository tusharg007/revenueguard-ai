"""Compact transition/click contact sheet for final human-visible QA."""
import json, math, subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;V=D/'final/revenueguard-buildathon-demo.mp4'
times=[63.7,64.3,74.7,75.3,98.7,99.3,138.7,139.3,162.7,163.3,198.7,199.3,215.7,216.3]
events=json.loads((D/'timeline.json').read_text(encoding='utf-8'))['events']
recorded=json.loads((D/'logs/events.json').read_text())
for s in ['batch','outage','approve','sandbox']:
    scene=next(e for e in events if e.get('source')==s)
    clicks=[e for e in recorded if e.get('shot')==s and e['type']=='click']
    for event in clicks:
        t=scene['timestamp']+event['offset'];times.extend([max(0,t-.3),t+.6])
sheet=Image.new('RGB',(1280,math.ceil(len(times)/4)*210),'#071a22');draw=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
    p=D/'work'/f'transition-{i}.jpg'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(V),'-frames:v','1',str(p)],check=True)
    x=i%4*320;y=i//4*210;sheet.paste(Image.open(p).resize((320,180)),(x,y));draw.text((x+8,y+184),f'{t:.2f}s',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17),fill='white')
sheet.save(D/'logs/final-transitions-and-clicks.jpg')
