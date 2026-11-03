"""Poly Haven (CC0) asset fetcher → assets/polyhaven/{hdris,textures,models}/<id>/.

    python -m reelforge.polyhaven hdri kloofendal_48d_partly_cloudy_puresky [--res 2k]
    python -m reelforge.polyhaven texture laminate_floor_02 [--res 2k]
    python -m reelforge.polyhaven model potted_plant_02 [--res 1k]
    python -m reelforge.polyhaven kit                      # the starter kit the 3D director uses

All Poly Haven assets are CC0 (no credit required). Files are cached; re-running skips what is on disk.
"""
import argparse
import sys
from pathlib import Path

import httpx

API = "https://api.polyhaven.com"
ROOT = Path(__file__).resolve().parents[2] / "assets" / "polyhaven"
HEAD = {"User-Agent": "ReelForge/1.0 (3d-director)"}
MAPS = {"Diffuse": "diff", "nor_gl": "nor", "Rough": "rough", "AO": "ao"}      # what director.pbr() reads

KIT = {
    "hdri": ["kloofendal_48d_partly_cloudy_puresky", "studio_small_09", "noon_grass", "blue_photo_studio"],
    "texture": ["laminate_floor_02", "plastered_wall", "wood_table_001", "fabric_pattern_07", "pavement_02",
                "leafy_grass", "red_brick_03", "concrete_floor_02", "asphalt_02", "metal_plate", "leather_red_02"],
    "model": ["potted_plant_02", "tree_small_02", "alarm_clock_01", "potted_plant_04", "fancy_picture_frame_01",
              "grass_medium_01"],
}


def _get(url, dst):
    if dst.exists() and dst.stat().st_size:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, headers=HEAD, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with open(dst, "wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    return dst


def files(asset_id):
    return httpx.get(f"{API}/files/{asset_id}", headers=HEAD, timeout=30).raise_for_status().json()


def hdri(asset_id, res="2k"):
    url = files(asset_id)["hdri"][res]["hdr"]["url"]
    return _get(url, ROOT / "hdris" / f"{asset_id}_{res}.hdr")


def texture(asset_id, res="2k"):
    f, out = files(asset_id), ROOT / "textures" / asset_id
    for key, short in MAPS.items():
        if key in f and res in f[key]:
            fmt = "jpg" if "jpg" in f[key][res] else next(iter(f[key][res]))
            _get(f[key][res][fmt]["url"], out / f"{short}.{fmt}")
    return out


def model(asset_id, res="1k"):
    g = files(asset_id)["gltf"][res]["gltf"]
    out = ROOT / "models" / asset_id
    main = _get(g["url"], out / Path(g["url"]).name)
    for rel, meta in g.get("include", {}).items():                       # textures + .bin next to the .gltf
        _get(meta["url"], out / rel)
    return main


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["hdri", "texture", "model", "kit"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--res")
    a = ap.parse_args(argv)
    jobs = [(k, i) for k, ids in KIT.items() for i in ids] if a.kind == "kit" else [(a.kind, i) for i in a.ids]
    fn = {"hdri": hdri, "texture": texture, "model": model}
    for kind, i in jobs:
        try:
            p = fn[kind](i, a.res) if a.res else fn[kind](i)
            print(f"ok  {kind:8s} {i} → {p.relative_to(ROOT)}")
        except Exception as e:                                          # keep going; report what failed
            print(f"ERR {kind:8s} {i}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
