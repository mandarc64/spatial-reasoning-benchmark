"""Create an editorial cover from executed PostGIS outputs. No image generation."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'spatial-benchmark-cover.png'
FONT=Path('C:/Windows/Fonts')
def font(size,bold=False):
    candidate=FONT/('arialbd.ttf' if bold else 'arial.ttf')
    if not candidate.exists():
        from matplotlib.font_manager import findfont, FontProperties
        candidate=Path(findfont(FontProperties(family='DejaVu Sans',weight='bold' if bold else 'normal')))
    return ImageFont.truetype(str(candidate),size)
im=Image.new('RGB',(1600,900),'#f5f5ef'); d=ImageDraw.Draw(im)
ink='#132f3e'; teal='#087e8b'; muted='#51636d'; orange='#d88230'
d.rectangle((0,0,20,900),fill=teal)
d.text((82,62),'SPATIAL REASONING  /  POSTGIS',font=font(24,True),fill=teal)
d.text((78,116),'A benchmark with',font=font(74,True),fill=ink)
d.text((78,202),'an answer key.',font=font(74,True),fill=ink)
d.text((82,310),'240 questions. Eight spatial tasks. Reproducible answers.',font=font(29),fill=muted)

left=(82,402,770,772); right=(804,402,1518,772)
for box in [left,right]:d.rounded_rectangle(box,radius=18,fill='white',outline='#dce3e0',width=2)
d.text((112,430),'NEAREST VS. WITHIN 100 KM',font=font(23,True),fill=ink)
rows=json.loads((ROOT/'airport_example.json').read_text())
for i,r in enumerate(rows):
    y=486+i*61; km=r['distance_m']/1000
    d.text((114,y),r['ident'],font=font(24,True),fill=ink)
    x=214; width=km/400*400
    d.rounded_rectangle((x,y+3,x+width,y+25),radius=3,fill=teal if km<=100 else '#bdc8ce')
    d.text((x+width+12,y),f'{km:.1f} km',font=font(22),fill=muted)
x=214+100/400*400
for y in range(480,727,12): d.line((x,y,x,y+6),fill=orange,width=3)
d.text((114,737),'Real airport coordinates; spheroidal distances.',font=font(19),fill=muted)

d.text((836,430),'THE BOUNDARY CHANGES THE ANSWER',font=font(23,True),fill=ink)
diagnostics=json.loads((ROOT/'predicate_diagnostics.json').read_text())
fields=['contains','covers','intersects']
for j,t in enumerate(['Contains','Covers','Intersects']):
    d.text((1022+j*151,479),t,font=font(19,True),fill=muted)
for i,r in enumerate(diagnostics[:3]):
    y=526+i*62
    label=['Interior','Boundary','Outside 0.5 m'][i]
    d.text((836,y+9),label,font=font(21),fill=ink)
    for j,f in enumerate(fields):
        x=1013+j*151; truth=r[f]
        d.rounded_rectangle((x,y,x+131,y+44),radius=6,fill=teal if truth else '#edf0f2')
        d.text((x+29,y+11),'TRUE' if truth else 'FALSE',font=font(19,True),fill='white' if truth else muted)
d.text((836,737),'Exact synthetic geometry; actual PostGIS outputs.',font=font(19),fill=muted)
d.text((82,825),'PUBLIC DATA  +  EXECUTABLE SQL  +  OPEN CODE',font=font(22,True),fill=teal)
d.text((1075,825),'LLM evaluation pending',font=font(22),fill=muted)
im.save(OUT)
print(OUT)
