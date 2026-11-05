#!/usr/bin/env python3
"""Razão de contraste WCAG 2.x entre duas cores.

Uso: python contrast.py "#ffffff" "#3b82f6"
"""
import sys


def parse(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"cor inválida: {h}")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(parse(a)), lum(parse(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    r = ratio(sys.argv[1], sys.argv[2])
    print(f"Contraste: {r:.2f}:1")
    print(f"  Texto normal AA  (4.5): {'OK' if r >= 4.5 else 'FALHA'}")
    print(f"  Texto grande AA  (3.0): {'OK' if r >= 3 else 'FALHA'}")
    print(f"  Componentes UI   (3.0): {'OK' if r >= 3 else 'FALHA'}")
    print(f"  Texto normal AAA (7.0): {'OK' if r >= 7 else 'FALHA'}")
