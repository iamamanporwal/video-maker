"""python sheet.py <dir> <out.jpg> [cols]: tile rendered frames into one contact sheet, labelled with seconds."""
import glob, sys
from PIL import Image, ImageDraw
fs = sorted(glob.glob(sys.argv[1] + "/f_*.jpg"))
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
ims = [Image.open(f) for f in fs]
w, h = ims[0].size
w2, h2 = w // 2, h // 2
sheet = Image.new("RGB", (w2 * cols, h2 * (-(-len(ims) // cols))), "black")
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * w2, (i // cols) * h2
    sheet.paste(im.resize((w2, h2)), (x, y))
    ImageDraw.Draw(sheet).text((x + 6, y + 6), f"{(int(f[-8:-4]) - 1) / 30:.1f}s", fill="red")
sheet.save(sys.argv[2])
