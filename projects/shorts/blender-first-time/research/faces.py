import json, urllib.request, urllib.parse, io, sys
from PIL import Image, ImageDraw
Q = ["shocked","angry","evil smile","crying","happy smile","scared","smirk","disgusted","nervous sweat","proud","sleepy","screaming"]
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20))
rows = []
for q in Q:
    try:
        r = get("https://apis.roblox.com/toolbox-service/v1/marketplace/13?limit=8&keyword=" + urllib.parse.quote("roblox face " + q))
        ids = [str(x["id"]) for x in r.get("data", [])][:6]
    except Exception as e:
        print(q, "ERR", e); ids = []
    rows.append((q, ids))
allids = [i for _, ids in rows for i in ids]
th = {}
for k in range(0, len(allids), 50):
    d = get("https://thumbnails.roblox.com/v1/assets?size=150x150&format=Png&assetIds=" + ",".join(allids[k:k+50]))
    for x in d["data"]: th[str(x["targetId"])] = x.get("imageUrl")
S = 150
sheet = Image.new("RGB", (S * 6 + 120, S * len(rows)), "white")
dr = ImageDraw.Draw(sheet)
meta = {}
for r, (q, ids) in enumerate(rows):
    dr.text((4, r * S + 60), q, fill="black")
    meta[q] = ids
    for c, i in enumerate(ids):
        u = th.get(i)
        if not u: continue
        try:
            im = Image.open(io.BytesIO(urllib.request.urlopen(u, timeout=20).read())).convert("RGBA")
            bg = Image.new("RGBA", im.size, (245, 205, 48, 255)); bg.alpha_composite(im)
            sheet.paste(bg.convert("RGB").resize((S, S)), (120 + c * S, r * S))
            dr.text((122 + c * S, r * S + 2), str(c), fill="red")
        except Exception as e: pass
sheet.save("faces.jpg", quality=85)
json.dump(meta, open("faces.json", "w"), indent=1)
print("ok")
