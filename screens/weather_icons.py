"""Geometric weather pictograms, rasterized above display resolution."""
import math
from PIL import Image, ImageDraw


def weather_icon(code, size=600):
    """Render scalable geometry with solid black strokes and smooth edge coverage.

    Coordinates use a 600-unit view box. Only downsampling is allowed: small
    bitmaps are never enlarged to create the displayed icon.
    """
    scale = size * 3 / 600
    image = Image.new('L', (size * 3, size * 3), 255)
    draw = ImageDraw.Draw(image)

    def ellipse(box, fill=0, outline=None, width=1):
        draw.ellipse(tuple(round(v * scale) for v in box), fill=fill,
                     outline=outline, width=max(1, round(width * scale)))

    def line(points, width=14):
        points = [(round(x*scale), round(y*scale)) for x,y in points]
        stroke = max(1, round(width*scale))
        draw.line(points, fill=0, width=stroke, joint='curve')
        for x,y in (points[0], points[-1]):
            r = stroke/2
            draw.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=0)

    def polygon(points):
        draw.polygon([(round(x*scale),round(y*scale)) for x,y in points],fill=0)

    def sun(cx=300, cy=300, radius=104, rays=range(0,360,45)):
        ellipse((cx-radius,cy-radius,cx+radius,cy+radius), fill=255, outline=0, width=14)
        for angle in rays:
            a=math.radians(angle)
            line([(cx+math.cos(a)*(radius+35),cy+math.sin(a)*(radius+35)),
                  (cx+math.cos(a)*(radius+88),cy+math.sin(a)*(radius+88))])

    def cloud(y=0):
        # Union of overlapping circles and a base: no internal seams.
        ellipse((108,246+y,258,396+y))
        ellipse((190,166+y,380,356+y))
        ellipse((320,224+y,492,396+y))
        polygon([(183,300+y),(406,300+y),(406,396+y),(183,396+y)])

    if code in (0,1):
        sun()
    elif code == 2:
        sun(218,210,74,rays=(0,180,225,270,315))
        cloud(28)
    elif code == 3:
        cloud()
    elif code in (45,48):
        cloud(-65)
        for y,w in [(378,320),(425,390),(472,260)]:
            line([(300-w/2,y),(300+w/2,y)],12)
    elif code in (51,53,55,56,57,61,63,65,66,67,80,81,82):
        cloud(-50)
        for x in (205,300,395):
            line([(x,402),(x-22,450 if code in (51,53,55,56,57) else 485)],14)
    elif code in (71,73,75,77,85,86):
        cloud(-65)
        for cx in (195,300,405):
            cy=440
            for angle in (0,60,120):
                a=math.radians(angle)
                dx,dy=30*math.cos(a),30*math.sin(a)
                line([(cx-dx,cy-dy),(cx+dx,cy+dy)],9)
    elif code in (95,96,99):
        cloud(-55)
        polygon([(303,377),(263,449),(304,449),(283,523),(365,420),(321,420),(345,377)])
    else:
        ellipse((178,178,422,422),fill=255,outline=0,width=14)
        line([(245,300),(355,300)])
    return image.resize((size,size),Image.Resampling.LANCZOS)
