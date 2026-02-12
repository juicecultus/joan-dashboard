#!/usr/bin/env python3
"""Generate a blurred preview image for the README — hides personal data.

Only blurs actual personal content (task names, event details, location).
Keeps all headings (To Do, Schedule, Today, This Week) and day labels
(Fri 13, Sat 14, etc.) visible.
"""
from PIL import Image, ImageFilter

img = Image.open("joan_preview.png")
R = 14  # blur radius

# Blur regions: only personal content, not structural elements
# Right column: B_R=820, indented events at B_R+12=832
# Left column: tasks start at B_L+36=76
blur_regions = [
    # To Do: task names only (after checkbox+gap, below heading)
    (76, 500, 760, 1150),
    # "No events today" or today's event text
    (832, 536, 1555, 565),
    # Event text lines under Fri 13 (indented at 832)
    (832, 695, 1555, 825),
    # Event text under Sat 14 (indented at 832)
    (832, 855, 1555, 900),
    # Footer: location name (bottom-left, before "Updated")
    (40, 1158, 185, 1190),
]

for box in blur_regions:
    region = img.crop(box)
    blurred = region.filter(ImageFilter.GaussianBlur(radius=R))
    img.paste(blurred, box)

img.save("docs/preview.png")
print("Saved docs/preview.png with blurred personal data")
