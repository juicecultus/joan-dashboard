"""Portrait-only photographs from Immich's read-only search and preview API."""
from .shared import *
from PIL import ImageOps
from pathlib import Path

PHOTOS_DIR = os.environ.get('PHOTOS_DIR', '')
IMMICH_URL = os.environ.get('IMMICH_URL', 'http://localhost:2283').rstrip('/')
IMMICH_API_KEY = os.environ.get('IMMICH_API_KEY', '')
_last_asset = None


def _portrait_image(content):
    """Orientation is checked on decoded pixels, after applying EXIF rotation."""
    with Image.open(BytesIO(content)) as source:
        photo = ImageOps.exif_transpose(source).convert('L')
    if photo.height <= photo.width:
        return None
    return photo


def _immich_photo():
    global _last_asset
    _require(IMMICH_API_KEY, 'Immich API key not configured')
    base = IMMICH_URL if IMMICH_URL.endswith('/api') else IMMICH_URL + '/api'
    headers = {'x-api-key': IMMICH_API_KEY}
    # Filter out videos and non-timeline assets on the server and again locally.
    response = requests.post(base + '/search/random', headers=headers,
        json={'size': 100, 'type': 'IMAGE', 'visibility': 'timeline', 'isOffline': False, 'withExif': True}, timeout=10)
    response.raise_for_status()
    assets = response.json()
    if not isinstance(assets, list):
        raise ScreenUnavailable('Unexpected Immich search response')
    candidates = []
    for asset in assets:
        if asset.get('type') != 'IMAGE' or asset.get('isTrashed') or asset.get('isArchived') or asset.get('isOffline'):
            continue
        if asset.get('visibility') != 'timeline':
            continue
        exif = asset.get('exifInfo') or {}
        w = asset.get('width') or exif.get('exifImageWidth')
        h = asset.get('height') or exif.get('exifImageHeight')
        orientation = str(exif.get('orientation',''))
        if w and h and h <= w and orientation not in ('5','6','7','8'):
            continue
        if asset.get('id'):
            candidates.append(asset)
    candidates.sort(key=lambda a: a['id'] == _last_asset)
    for asset in candidates[:8]:
        try:
            result = requests.get(base + '/assets/' + asset['id'] + '/thumbnail',
                headers=headers, params={'size': 'preview'}, timeout=6, allow_redirects=False)
            result.raise_for_status()
            if result.status_code != 200:
                continue
            photo = _portrait_image(result.content)
            if photo is not None:
                _last_asset = asset['id']
                return _picture(photo)
        except (requests.RequestException, OSError, ValueError):
            continue
    raise ScreenUnavailable('No readable portrait photos returned by Immich')


def render_family_photo():
    if IMMICH_API_KEY or not PHOTOS_DIR:
        return _immich_photo()
    # Optional local-folder fallback also obeys the portrait-only rule.
    directory = Path(PHOTOS_DIR)
    extensions = {'.jpg','.jpeg','.png','.bmp','.webp'}
    photos = [f for f in directory.rglob('*') if f.suffix.lower() in extensions] if directory.is_dir() else []
    random.shuffle(photos)
    for path in photos:
        try:
            photo = _portrait_image(path.read_bytes())
            if photo is not None:
                return _picture(photo)
        except (OSError, ValueError):
            continue
    raise ScreenUnavailable('Photo folder contains no readable portrait photos')
