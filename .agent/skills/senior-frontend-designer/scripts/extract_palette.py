#!/usr/bin/env python3
"""Extrai a paleta dominante de uma imagem (Pillow) e sugere papéis de cor.

Uso: python extract_palette.py imagem.png [-n 8] [--json]
"""
import argparse
import json
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow não instalado: pip install pillow --break-system-packages")


def luminance(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def saturation(rgb):
    mx, mn = max(rgb), min(rgb)
    return 0 if mx == 0 else (mx - mn) / mx


def extract(path, n):
    img = Image.open(path).convert("RGB")
    img.thumbnail((320, 320))
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    out = []
    for count, idx in counts:
        rgb = tuple(pal[idx * 3 : idx * 3 + 3])
        out.append({"hex": "#%02x%02x%02x" % rgb, "rgb": rgb, "share": round(100 * count / total, 1),
                    "luminance": round(luminance(rgb), 3), "saturation": round(saturation(rgb), 2)})
    return out


def suggest_roles(colors):
    roles = {}
    if not colors:
        return roles
    roles["--color-bg (mais frequente)"] = colors[0]["hex"]
    vivid = [c for c in colors if c["saturation"] > 0.35 and 0.05 < c["luminance"] < 0.8]
    if vivid:
        roles["--color-primary (mais saturada frequente)"] = max(vivid, key=lambda c: c["share"])["hex"]
    dark = min(colors, key=lambda c: c["luminance"])
    light = max(colors, key=lambda c: c["luminance"])
    roles["mais escura (texto/fundo escuro)"] = dark["hex"]
    roles["mais clara (superfície/texto claro)"] = light["hex"]
    return roles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("-n", type=int, default=8, help="número de cores (2-16)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    colors = extract(a.image, max(2, min(16, a.n)))
    roles = suggest_roles(colors)
    if a.json:
        print(json.dumps({"colors": colors, "roles": roles}, ensure_ascii=False, indent=2))
        return
    print("Cores dominantes:")
    for c in colors:
        print(f"  {c['hex']}  {c['share']:>5}%  lum={c['luminance']}  sat={c['saturation']}")
    print("\nSugestão de papéis (confirme olhando a imagem):")
    for k, v in roles.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
