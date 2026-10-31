"""Photo-only, final-pixel conversion for the Joan's sixteen gray levels.

Full-tone sources and text stay untouched. The caller must finish all resizing
and rotation before applying the ordered pattern. Uses the same standard 8x8
Bayer matrix and +/-8 bias as Reader's grey.rs.
"""
from PIL import Image

BAYER = (
    (0,32,8,40,2,34,10,42),
    (48,16,56,24,50,18,58,26),
    (12,44,4,36,14,46,6,38),
    (60,28,52,20,62,30,54,22),
    (3,35,11,43,1,33,9,41),
    (51,19,59,27,49,17,57,25),
    (15,47,7,39,13,45,5,37),
    (63,31,55,23,61,29,53,21),
)

_TABLES = tuple(tuple(bytes(
    ((max(0,min(255,g + t*17//64-8))*30+255)//510)*17
    for g in range(256)) for t in row) for row in BAYER)


def dither_photos(image, mask):
    """Dither only white pixels of mask, anchored to final panel coordinates."""
    if mask.size != image.size:
        raise ValueError('Photo mask must match final display pixels')
    gray = image.convert('L')
    source = gray.tobytes()
    output = bytearray(source)
    width, height = gray.size
    # Strided byte translation keeps this inexpensive without a NumPy dependency.
    for y in range(height):
        row = source[y*width:(y+1)*width]
        for phase, table in enumerate(_TABLES[y%8]):
            output[y*width+phase:(y+1)*width:8] = row[phase::8].translate(table)
    dithered = Image.frombytes('L',gray.size,bytes(output))
    return Image.composite(dithered,gray,mask)
