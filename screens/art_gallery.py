from .shared import *

# Public-domain paintings, addressed directly: the Met search endpoint was retired.
_ART_IDS = [436535, 436532, 437853, 436121, 437133, 436105]


def _fetch_art():
    offset = datetime.now().toordinal() % len(_ART_IDS)
    for object_id in (_ART_IDS[offset:] + _ART_IDS[:offset]):
        try:
            r = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}", timeout=10)
            r.raise_for_status()
            obj = r.json()
            if not obj.get("isPublicDomain"):
                continue
            picture = _image_url(obj.get("primaryImage") or obj.get("primaryImageSmall"))
            if picture is not None:
                return {"image": picture, "title": obj['title'], "artist": obj.get('artistDisplayName','')}
        except Exception as exc:
            print(f"[art] Object {object_id} unavailable: {type(exc).__name__}")
    raise ScreenUnavailable("Museum artwork unavailable")


def render_art_gallery():
    art = _require(_cache_fetch("art_v2", 86400, 604800, _fetch_art))
    return _picture(art['image'], art['title'], credit='by '+art['artist'] if art['artist'] else '', editorial=True)
