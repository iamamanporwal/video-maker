"""thumbs.py out.jpg id1 id2 ... → labelled sheet of Roblox asset thumbnails (420px)."""
import json, urllib.request, io, sys
from PIL import Image, ImageDraw
out, ids = sys.argv[1], sys.argv[2:]
UA = {"User-Agent": "Mozilla/5.0"}
d = json.load(urllib.request.urlopen(urllib.request.Request("https://thumbnails.roblox.com/v1/assets?size=420x420&format=Png&assetIds=" + ",".join(ids), headers=UA)))
th = {str(x["targetId"]): x.get("imageUrl") for x in d["data"]}
S, C = 300, 4
sheet = Image.new("RGB", (S * C, S * ((len(ids) + C - 1) // C)), "white"); dr = ImageDraw.Draw(sheet)
for n, i in enumerate(ids):
    x, y = (n % C) * S, (n // C) * S
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(th[i], timeout=20).read())).convert("RGB").resize((S, S)); sheet.paste(im, (x, y))
    except Exception: pass
    dr.rectangle([x, y, x + 150, y + 16], fill="black"); dr.text((x + 3, y + 2), f"{n}:{i}", fill="yellow")
sheet.save(out, quality=80); print("ok")
