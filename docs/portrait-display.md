# Portrait room display

The 13-inch Joan is mounted **90 degrees clockwise (to the right)** from its original landscape orientation. Screens render at **1200 × 1600**. The delivery layer rotates each frame 90 degrees counterclockwise into the device's native 1600 × 1200 framebuffer. There is no VSS orientation change and no stretching. `PORTRAIT_ROTATION=270` is available for the opposite mounting direction.

Each frame focuses on one subject: one headline, movie, task, event, stock, collection day, or learning question. Generic headers, update timestamps, battery details and footer bars are removed. Artwork/quote attribution and map copyright remain content-specific. The `dashboard` playlist entry now displays current weather; `agenda` and `todo` remain separately selectable.

## Feed repairs

- Art uses known public-domain Met object endpoints, avoiding the retired search endpoint; tries another painting if its image fails.
- BBC uses the official BBC RSS feed rather than an unreliable third-party news API.
- Buddha quotes are local, explicitly attributed Dhammapada paraphrases, replacing the dead domain.
- RSS requests have a timeout and a browser user agent (The Verge rejects the default requests user agent).
- GitHub reads the real trending page; doodles use an HTML parser rather than attribute-order-sensitive regex.
- Air quality requests only European AQI; the old request included an unsupported UV field.
- Moon geometry uses a cosine terminator with correct new/full and waxing/waning illumination.
- A failed or empty fetch cannot overwrite a usable in-memory cache. Unavailable screens leave the last useful frame intact and advance after five seconds, rather than publishing an error for three minutes.
- Trains do not fall back to half-hour-old departure information. Only the configured destination is shown.

## Immich photos

On Max, add to the existing private `.env`:

```
IMMICH_URL=http://localhost:2283
IMMICH_API_KEY=your-private-key
```

Create the key in Immich Account Settings → API Keys with only `asset.read` and `asset.view`. The integration uses `POST /api/search/random` and `GET /api/assets/{id}/thumbnail?size=preview`. It does not modify Immich assets. Videos, hidden/locked/archived/trashed/offline assets are excluded. Dimensions and decoded, EXIF-oriented pixels are checked; landscape and square photos are never displayed. Images retain their proportions and are not cropped. The previous photo is avoided when alternatives are available.

Without a key, an explicitly configured `PHOTOS_DIR` remains an optional portrait-only fallback. A missing folder is never created automatically.

## Validation

Use Python 3.10 or newer and install `requirements.txt`:

```
python -m unittest discover -s tests -v
python tools/audit_screens.py portrait-previews
```

The audit renders all registered screens without starting the delivery service or pushing images. It writes a status report and contact sheets. Audit images can include private calendar entries, tasks or photos and are ignored by Git. Tests cover mounting direction, scaling, text bounds, lunar illumination, cache recovery, train payload normalization, and portrait-photo selection.

## Buckinghamshire bin migration

On 31 October 2026 the retired `kmbd/collectionDay` endpoint returned a valid encrypted response containing `collectionDay: null`, even for a valid address. The replacement uses the council's `gdsv5` form service: create a lookup session, discover the web-service field and its input mapping, then read its collection table. The adapter follows the updated [UKBinCollectionData implementation](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/BuckinghamshireCouncil.py); its MIT notice is retained in `docs/third-party`.

The renderer groups all bins due on the next collection day, excludes past dates and does not extrapolate a recurring schedule. Yearless dates are inferred only within the next 90 days, including a year boundary. The live lookup and portrait render were verified on Max.
