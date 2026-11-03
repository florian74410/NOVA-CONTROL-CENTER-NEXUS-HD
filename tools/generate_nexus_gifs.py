#!/usr/bin/env python3
"""Generate original transparent NEXUS GIF animations. No third-party art used.

Requires Pillow. Re-running reproduces the same frames. CLI:
  python tools/generate_nexus_gifs.py
"""
from __future__ import annotations
from pathlib import Path
from math import sin, cos, pi
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]/"Assets"/"Generated"/"Animations"
THEMES={
    "ElectroBlueNEON":(0,216,255),
    "RougeERROR":(255,43,76),
}
SIZE=72
FRAMES=18

def frame(kind,index,color):
    im=Image.new("RGBA",(SIZE,SIZE),(0,0,0,0))
    d=ImageDraw.Draw(im,"RGBA")
    t=index/FRAMES
    r,g,b=color
    def ink(a=255):return (r,g,b,a)
    if kind=="pulse":
        for k in range(3):
            rad=8+((t+k/3)%1)*24
            alpha=int(190*(1-((t+k/3)%1)))
            d.ellipse((36-rad,36-rad,36+rad,36+rad),
                      outline=ink(alpha),width=2)
        d.ellipse((32,32,40,40),fill=ink(240))
    elif kind=="loader":
        for k in range(12):
            angle=2*pi*k/12
            x,y=36+23*cos(angle),36+23*sin(angle)
            alpha=int(35+220*((k-index)%12)/12)
            d.ellipse((x-3,y-3,x+3,y+3),fill=ink(alpha))
    elif kind=="check":
        c=36
        radius=22
        d.ellipse((c-radius,c-radius,c+radius,c+radius),outline=ink(130),width=2)
        points=[(23,37),(32,46),(50,27)]
        progress=(index+1)/FRAMES*2
        if progress<=1:
            p=(points[0][0]+(points[1][0]-points[0][0])*progress,
               points[0][1]+(points[1][1]-points[0][1])*progress)
            d.line([points[0],p],fill=ink(255),width=5)
        else:
            d.line(points[:2],fill=ink(255),width=5)
            p=(points[1][0]+(points[2][0]-points[1][0])*(progress-1),
               points[1][1]+(points[2][1]-points[1][1])*(progress-1))
            d.line([points[1],p],fill=ink(255),width=5)
    elif kind=="alert":
        alpha=int(90+160*abs(sin(t*pi*2)))
        points=[(36,9),(63,57),(9,57),(36,9)]
        d.line(points,fill=ink(alpha),width=3,joint="curve")
        d.line([(36,25),(36,42)],fill=ink(255),width=5)
        d.ellipse((33,48,39,54),fill=ink(255))
    elif kind=="data":
        for k in range(9):
            x=10+7*k
            h=int(9+42*abs(sin(t*pi*2+k*.6)))
            d.rounded_rectangle((x,36-h//2,x+4,36+h//2),radius=2,
                                fill=ink(80+int(140*abs(sin(t*pi*2+k*.4)))))
    elif kind=="pcb":
        x=int(7+t*58)
        d.line([(6,50),(23,50),(36,37),(64,37)],fill=ink(78),width=2)
        d.ellipse((60,33,68,41),outline=ink(130),width=2)
        d.ellipse((max(2,x-4),46,max(10,x+4),54),fill=ink(255))
    return im

def save(kind,folder,color):
    images=[frame(kind,k,color) for k in range(FRAMES)]
    # Fixed indexed palette: index 0 genuinely transparent, no matte/checkerboard.
    pal=[0,0,0, color[0],color[1],color[2]]+[0,0,0]*254
    indexed=[]
    for im in images:
        out=Image.new("P",im.size,0)
        out.putpalette(pal)
        src=im.load()
        dst=out.load()
        # GIF 1-bit transparency: no background, preserve the bright strokes.
        for y in range(SIZE):
            for x in range(SIZE):
                if src[x,y][3]>=45:dst[x,y]=1
        out.info["transparency"]=0
        indexed.append(out)
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(kind+".gif")
    indexed[0].save(target,save_all=True,append_images=indexed[1:],
                    duration=65,loop=0,disposal=2,transparency=0,optimize=False)
    print(target)

def main():
    for theme,color in THEMES.items():
        directory=ROOT/theme
        for kind in ("pulse","loader","check","alert","data","pcb"):
            save(kind,directory,color)
    (ROOT/"README.md").write_text(
        "# NEXUS original GIF animations\n"
        "Six original procedural effects in two palettes (12 transparent GIFs).\n"
        "Generated from code in tools/generate_nexus_gifs.py using Pillow.\n"
        "Transparent pixels use GIF palette index 0; no photographic assets or watermarks.\n"
        "Qt's native QPainter animations remain the default for performance.\n",
        encoding="utf-8")
if __name__=="__main__":
    main()
