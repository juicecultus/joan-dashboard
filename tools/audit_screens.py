"""Render every screen without starting a server or pushing to a device."""
import concurrent.futures
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screens.registry import ALL_SCREENS
from screens.shared import ScreenUnavailable
from joan_dashboard import render_dashboard

out = Path(sys.argv[1] if len(sys.argv)>1 else 'portrait-previews')
out.mkdir(parents=True, exist_ok=True)

def render(item):
    name, fn = item
    try:
        img = fn()
        assert img.size == (1200,1600), img.size
        assert img.mode == 'L', img.mode
        assert ImageStat.Stat(img).stddev[0] > 5, 'Empty image'
        img.save(out / (name+'.png'))
        return name, 'OK'
    except ScreenUnavailable as exc:
        return name, 'UNAVAILABLE: '+str(exc)
    except Exception as exc:
        return name, 'ERROR: '+type(exc).__name__+': '+str(exc)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = dict(pool.map(render, [('dashboard',render_dashboard)]+list(ALL_SCREENS.items())))
(out/'audit.json').write_text(json.dumps(results,indent=2))
for name, status in results.items(): print(name, status, flush=True)
files = sorted(out.glob('*.png'))
for page in range((len(files)+11)//12):
    sheet = Image.new('RGB',(1200,1680),'#ddd')
    draw = ImageDraw.Draw(sheet)
    for i,path in enumerate(files[page*12:(page+1)*12]):
        x,y=(i%4)*300,(i//4)*560
        im = Image.open(path); im.thumbnail((288,510)); sheet.paste(im,(x+6,y+30))
        draw.text((x+12,y+8),path.stem,fill='black')
    sheet.save(out/f'contact-{page+1}.jpg')
if any(s.startswith('ERROR') for s in results.values()): sys.exit(1)
