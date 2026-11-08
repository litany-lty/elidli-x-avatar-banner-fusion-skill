#!/usr/bin/env python3
"""Create a generic non-personal 3:1 demo banner for the geometry preview."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

p=argparse.ArgumentParser()
p.add_argument('--out',default='output/demo_banner.png')
p.add_argument('--width',type=int,default=1536)
a=p.parse_args()
w=a.width
if w <= 0 or w % 3: raise SystemExit('--width must be a positive multiple of 3')
h=w//3
img=Image.new('RGB',(w,h)); px=img.load()
for y in range(h):
    for x in range(w):
        t=x/w; u=y/h
        px[x,y]=(int(5+35*t),int(7+9*u),int(18+20*(1-t)))
d=ImageDraw.Draw(img)
scale=w/1536
curve=[]
for x in range(w):
    xv=x/scale
    # avatar crown is only a SHALLOW arch near the lower edge.
    yv=(459 + 0.00195*(xv-210)**2) if xv<=400 else 506-36*__import__('math').sin((xv-400)/1100*__import__('math').pi)
    if yv<512: curve.append((x,int(round(yv*scale))))
if len(curve)>1:
    d.line(curve,fill=(247,151,53),width=max(2,int(7*scale)),joint='curve')
    d.line(curve,fill=(247,224,151),width=max(1,int(2*scale)))
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);img.save(out)
print(out)
