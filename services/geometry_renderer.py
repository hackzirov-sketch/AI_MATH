"""
services/geometry_renderer.py  —  V2.0

Shakl kutubxonasi:
  Mavjud  : right_triangle, isosceles_triangle, equilateral_triangle,
            obtuse_triangle, triangle (acute),
            rectangle, circle, hexagon,
            crossword, labyrinth, grid, scale
  YANGI   : trapezoid   (trapeziya)
            rhombus      (romb)
            parallelogram
            coordinate   (koordinat tekislik)
            number_line  (son o'qi)
            bar_chart    (ustunli diagramma)
            pie_chart    (doira diagramma)
            clock        (soat)

Vizual yaxshilanishlar V2:
  - Har bir shakl uchun rang to'ldirish (facecolor)
  - Dimension o'qchalari (<->)
  - Teng tomonlar uchun tick belgilari
  - Noma'lum (x, ?) → qizil, kattaroq
  - Deterministic seed (bir xil hint = bir xil rasm)
  - Burchak yoylari (Arc) barcha uchburchaklarda
"""

import hashlib
import math
import os
import random as _random
import re
import threading
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.patches import Arc
import numpy as np
from services.cache_manager import cache_manager

# ─── Papka ───────────────────────────────────────────────────────────────────
plot_lock = threading.Lock()
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMP_DIR = str(cache_manager.render_dir)

# ─── Rang palitasi ────────────────────────────────────────────────────────────
_FILL = {
    "triangle": "#eff6ff",
    "rectangle": "#f0fdf4",
    "trapezoid": "#f0f9ff",
    "rhombus": "#fdf4ff",
    "parallelogram": "#fff1f2",
    "circle": "#fff7ed",
    "hexagon": "#fefce8",
    "neutral": "#f8fafc",
}
_EDGE = "#1e293b"
_UNK_CLR = "#e11d48"
_ANG_CLR = "#7c3aed"
_AUX_CLR = "#94a3b8"
_TXT_DARK = "#1e293b"
_BAR_COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
]
_PIE_COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
]


# ═════════════════════════════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR
# ═════════════════════════════════════════════════════════════════════════════


def _hint_seed(hint: str) -> int:
    return int(hashlib.md5(hint.encode()).hexdigest()[:8], 16)


def _parse_numeric(val, default: float = 4.0) -> float:
    if not val or str(val).strip().lower() in ("x", "?", "null", ""):
        return default
    m = re.search(r"(\d+\.?\d*)", str(val))
    return float(m.group(1)) if m else default


def _is_unknown(val) -> bool:
    return str(val).strip().lower() in ("x", "?", "x2", "x^2", "x²", "...")


def _lc(val) -> str:
    """Label color: qizil → noma'lum, qora → ma'lum."""
    return _UNK_CLR if _is_unknown(val) else _TXT_DARK


def _ls(val, base: int = 14) -> int:
    """Label size: noma'lum kattaroq."""
    return base + 4 if _is_unknown(val) else base


def _dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _unit(a, b):
    d = max(_dist(a, b), 1e-9)
    return (b[0] - a[0]) / d, (b[1] - a[1]) / d


def _perp(ux, uy):
    return -uy, ux


def _rotate_pts(pts, deg, cx=0.0, cy=0.0):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [
        [cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca]
        for x, y in pts
    ]


def _centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


# ─── Burchak yoyi ─────────────────────────────────────────────────────────────
def _angle_arc(ax, vtx, p1, p2, r=0.38, color=_ANG_CLR):
    a1 = math.degrees(math.atan2(p1[1] - vtx[1], p1[0] - vtx[0])) % 360
    a2 = math.degrees(math.atan2(p2[1] - vtx[1], p2[0] - vtx[0])) % 360
    t1, t2 = min(a1, a2), max(a1, a2)
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    ax.add_patch(
        Arc(
            (vtx[0], vtx[1]),
            r * 2,
            r * 2,
            angle=0,
            theta1=t1,
            theta2=t2,
            color=color,
            linewidth=1.4,
        )
    )


# ─── Tomon o'rtasiga label ────────────────────────────────────────────────────
def _side_lbl(ax, pa, pb, text, extra=0.0, side=1):
    mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    ux, uy = _unit(pa, pb)
    nx, ny = _perp(ux, uy)
    off = max(_dist(pa, pb) * 0.14, 0.28) + extra
    ax.text(
        mx + nx * off * side,
        my + ny * off * side,
        text,
        fontsize=_ls(text),
        color=_lc(text),
        fontweight="bold",
        ha="center",
        va="center",
    )


# ─── Dimension o'qchasi (<->) ─────────────────────────────────────────────────
def _dim(ax, p1, p2, label, gap=0.40, clr=_AUX_CLR):
    ux, uy = _unit(p1, p2)
    nx, ny = _perp(ux, uy)
    ax.annotate(
        "",
        xy=(p2[0] + nx * gap, p2[1] + ny * gap),
        xytext=(p1[0] + nx * gap, p1[1] + ny * gap),
        arrowprops=dict(arrowstyle="<->", color=clr, lw=1.4),
    )
    mx = (p1[0] + p2[0]) / 2 + nx * (gap + 0.24)
    my = (p1[1] + p2[1]) / 2 + ny * (gap + 0.24)
    ax.text(
        mx,
        my,
        label,
        fontsize=_ls(label),
        color=_lc(label),
        fontweight="bold",
        ha="center",
        va="center",
    )


# ─── To'g'ri burchak kvadratchasi ─────────────────────────────────────────────
def _right_sq(ax, vtx, p1, p2, sz=0.22):
    u1 = _unit(vtx, p1)
    u2 = _unit(vtx, p2)
    sq = [
        [vtx[0] + u1[0] * sz, vtx[1] + u1[1] * sz],
        [vtx[0] + u1[0] * sz + u2[0] * sz, vtx[1] + u1[1] * sz + u2[1] * sz],
        [vtx[0] + u2[0] * sz, vtx[1] + u2[1] * sz],
    ]
    ax.add_patch(
        patches.Polygon(sq, closed=False, fill=False, edgecolor=_EDGE, linewidth=1.4)
    )


# ─── Teng tomonlar tick ───────────────────────────────────────────────────────
def _ticks(ax, p1, p2, n=1, clr=_EDGE):
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    ux, uy = _unit(p1, p2)
    nx, ny = _perp(ux, uy)
    tl, sp = 0.18, 0.13
    for i in range(n):
        off = (i - (n - 1) / 2) * sp
        tx, ty = mx + ux * off, my + uy * off
        ax.plot(
            [tx - nx * tl / 2, tx + nx * tl / 2],
            [ty - ny * tl / 2, ty + ny * tl / 2],
            color=clr,
            lw=1.6,
        )


# ─── Vertex label ─────────────────────────────────────────────────────────────
def _vlbl(ax, pt, ctr, lbl, off=0.45):
    cx, cy = ctr
    dx, dy = pt[0] - cx, pt[1] - cy
    d = max(math.hypot(dx, dy), 1e-9)
    ax.text(
        pt[0] + dx / d * off,
        pt[1] + dy / d * off,
        lbl,
        fontsize=12,
        fontweight="bold",
        color=_TXT_DARK,
        ha="center",
        va="center",
    )


# ═════════════════════════════════════════════════════════════════════════════
# create_diagram  —  Asosiy kirish nuqtasi
# ═════════════════════════════════════════════════════════════════════════════


def create_diagram(hint: str):
    """
    Geometry hint stringidan rasm yoki video yaratadi.
    Qaytaradi: fayl yo'li (str) yoki None.
    """
    if not hint or str(hint).lower() == "null" or not str(hint).strip():
        return None

    # Manim mavjud bo'lsa video
    try:
        from services.manim_engine import create_manim_video

        vp = create_manim_video(hint)
        if vp and os.path.exists(vp):
            return vp
    except Exception:
        pass

    os.makedirs(_TEMP_DIR, exist_ok=True)
    filepath = os.path.join(_TEMP_DIR, f"geom_{uuid.uuid4().hex[:8]}.png")
    seed = _hint_seed(hint)
    items: dict = {}

    # Hint ni parse qilish
    if "|" in hint:
        parts = hint.split("|")
        st = parts[0].strip().lower()
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                items[k.strip().lower()] = v.strip()
    else:
        parts = hint.split(";")
        st = parts[0].strip().lower()
        for i, p in enumerate(parts[1:], 1):
            if p.strip():
                items[f"val{i}"] = p.strip()

    with plot_lock:
        # O'lcham
        if any(x in st for x in ("bar_chart", "bar")):
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.set_aspect("auto")
        elif any(x in st for x in ("pie_chart", "pie")):
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.set_aspect("equal")
        elif any(x in st for x in ("coordinate", "koordinat")):
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.set_aspect("equal")
        elif any(x in st for x in ("number_line", "son_osi")):
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.set_aspect("auto")
        else:
            fig, ax = plt.subplots(figsize=(5.5, 5.5))
            ax.set_aspect("equal")

        ax.axis("off")
        fig.patch.set_facecolor("white")

        # Dispatch
        if "right_triangle" in st:
            draw_triangle(ax, items, "right", seed)
        elif "isosceles_triangle" in st:
            draw_triangle(ax, items, "isosceles", seed)
        elif "equilateral_triangle" in st:
            draw_triangle(ax, items, "equilateral", seed)
        elif "obtuse_triangle" in st:
            draw_triangle(ax, items, "obtuse", seed)
        elif "triangle" in st:
            draw_triangle(ax, items, "acute", seed)
        elif "trapezoid" in st or "trapeziya" in st:
            draw_trapezoid(ax, items, seed)
        elif "rhombus" in st or "romb" in st:
            draw_rhombus(ax, items, seed)
        elif "parallelogram" in st:
            draw_parallelogram(ax, items, seed)
        elif "hexagon" in st or "oltiburchak" in st:
            draw_hexagon(ax, items, seed)
        elif "rectangle" in st or "square" in st:
            draw_rectangle(ax, items, seed)
        elif "circle" in st or "doira" in st or "aylana" in st:
            draw_circle(ax, items, seed)
        elif "coordinate" in st or "koordinat" in st:
            draw_coordinate(ax, items, seed)
        elif "number_line" in st or "son_osi" in st:
            draw_number_line(ax, items, seed)
        elif "bar_chart" in st or st == "bar":
            draw_bar_chart(ax, items, seed)
        elif "pie_chart" in st or st == "pie":
            draw_pie_chart(ax, items, seed)
        elif "clock" in st or "soat" in st:
            draw_clock(ax, items, seed)
        elif "crossword" in st or "krossvord" in st:
            draw_crossword(ax, items, seed)
        elif "labyrinth" in st or "labirint" in st:
            draw_labyrinth(ax, items, seed)
        elif "grid" in st:
            draw_logic_grid(ax, items, seed)
        elif "scale" in st:
            draw_scale(ax, items, seed)
        elif "incenter" in st or "inmarkaz" in st or "centers" in st:
            draw_triangle_centers(ax, items, seed)
        elif "ceva" in st:
            draw_ceva_theorem(ax, items, seed)
        elif "menelaus" in st or "menelay" in st:
            draw_menelaus_theorem(ax, items, seed)
        elif "stewart" in st or "styuart" in st:
            draw_stewart_theorem(ax, items, seed)
        elif "ptolemy" in st or "ptolemey" in st:
            draw_ptolemy_theorem(ax, items, seed)
        elif "varignon" in st or "varinyon" in st:
            draw_varignon_theorem(ax, items, seed)
        elif "homothety" in st or "gomotetiya" in st or "oxshashlik" in st:
            draw_homothety(ax, items, seed)
        elif "vector" in st or "vektor" in st:
            draw_vector_geometry(ax, items, seed)
        elif "sin_cos" in st or "sinus" in st or "kosinus" in st:
            draw_sin_cos_theorem(ax, items, seed)
        elif "circumscribed" in st or "tashqi_chizilgan" in st:
            draw_circumscribed_quad(ax, items, seed)
        elif "heron" in st or "geron" in st:
            draw_heron_formula(ax, items, seed)
        elif "pythagoras" in st or "pifagor" in st:
            draw_pythagoras_detailed(ax, items, seed)
        else:
            draw_triangle(ax, items, "acute", seed)

        plt.tight_layout(pad=0.4)
        plt.savefig(filepath, dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    return filepath


# ═════════════════════════════════════════════════════════════════════════════
# UCHBURCHAKLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_triangle(ax, items: dict, subtype="acute", seed=42):
    """
    Barcha uchburchak turlari: right, isosceles, equilateral, obtuse, acute.
    Haqiqiy nisbatlar hint qiymatlaridan, kichik rotation seed dan.
    """
    rng = _random.Random(seed)
    b = _parse_numeric(items.get("bottom", "4"), 4.0)
    l = _parse_numeric(items.get("left", "3"), 3.0)
    mx_v = max(b, l, 0.1)
    sc = 5.0 / mx_v
    bs, ls = b * sc, l * sc
    pts: list = []
    rot = 0.0
    right_vtx = 0  # to'g'ri burchak tepa indeksi

    if subtype == "right":
        pts = [[0.0, 0.0], [bs, 0.0], [0.0, ls]]
        right_vtx = 0

    elif subtype == "isosceles":
        hb = bs / 2
        ht = math.sqrt(max(ls**2 - hb**2, 0.4)) if ls > hb else ls * 0.9
        pts = [[0.0, 0.0], [bs, 0.0], [hb, ht]]
        rot = rng.uniform(-6.0, 6.0)

    elif subtype == "equilateral":
        pts = [[0.0, 0.0], [bs, 0.0], [bs / 2, bs * math.sqrt(3) / 2]]
        rot = rng.uniform(-8.0, 8.0)

    elif subtype == "obtuse":
        ov = rng.uniform(0.8, 1.6) * sc
        ht = rng.uniform(1.5, 2.8) * sc
        pts = [[0.0, 0.0], [bs, 0.0], [-ov, ht]]
        rot = rng.uniform(-5.0, 5.0)

    else:  # acute
        a1 = rng.uniform(48.0, 72.0)
        a2 = rng.uniform(48.0, 72.0)
        if a1 + a2 >= 174:
            a1, a2 = 58.0, 64.0
        cx2 = ls * math.cos(math.radians(a1))
        cy2 = ls * math.sin(math.radians(a1))
        pts = [[0.0, 0.0], [bs, 0.0], [cx2, cy2]]
        rot = rng.uniform(-5.0, 5.0)

    if abs(rot) > 0.01:
        cxc, cyc = _centroid(pts)
        pts = _rotate_pts(pts, rot, cxc, cyc)

    # Shakl (rang to'ldirilgan)
    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(
            pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2
        )
    )

    # To'g'ri burchak belgisi
    if subtype == "right":
        _right_sq(ax, pts[right_vtx], pts[1], pts[2], sz=min(bs, ls) * 0.09)

    # Burchak yoylari
    sides = [_dist(pts[0], pts[1]), _dist(pts[1], pts[2]), _dist(pts[0], pts[2])]
    ar = max(min(sides) * 0.18, 0.18)
    for i, (v, p1, p2) in enumerate(
        [
            (pts[0], pts[1], pts[2]),
            (pts[1], pts[0], pts[2]),
            (pts[2], pts[0], pts[1]),
        ]
    ):
        if subtype == "right" and i == right_vtx:
            continue
        _angle_arc(ax, v, p1, p2, r=ar)

    # Teng tomonlar tick
    if subtype == "isosceles":
        _ticks(ax, pts[0], pts[2], n=1)
        _ticks(ax, pts[1], pts[2], n=1)
    if subtype == "equilateral":
        _ticks(ax, pts[0], pts[1], n=2)
        _ticks(ax, pts[1], pts[2], n=2)
        _ticks(ax, pts[0], pts[2], n=2)

    # Vertex harflari
    ctr = _centroid(pts)
    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(
            pt[0] + dx / d * 0.48,
            pt[1] + dy / d * 0.48,
            lbl,
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
            zorder=5,
        )

    # Tomon labellar
    ar_txt = ar * 2.2
    if "bottom" in items:
        _side_lbl(ax, pts[0], pts[1], items["bottom"])
    if "left" in items:
        _side_lbl(ax, pts[0], pts[2], items["left"])
    if "right" in items:
        _side_lbl(ax, pts[1], pts[2], items["right"], side=-1)

    # Burchak labellar
    def _ang_txt(vtx_idx, key):
        if key not in items:
            return
        v = items[key]
        p1 = pts[(vtx_idx + 1) % 3]
        p2 = pts[(vtx_idx + 2) % 3]
        u1 = _unit(pts[vtx_idx], p1)
        u2 = _unit(pts[vtx_idx], p2)
        r2 = ar * 2.4
        ax.text(
            pts[vtx_idx][0] + (u1[0] + u2[0]) / 2 * r2,
            pts[vtx_idx][1] + (u1[1] + u2[1]) / 2 * r2,
            v,
            fontsize=_ls(v) - 2,
            color=_lc(v),
            fontweight="bold",
            ha="center",
            va="center",
            zorder=5,
        )

    _ang_txt(0, "angle_a")
    _ang_txt(1, "angle_b")
    _ang_txt(2, "angle_c")

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = max(bs, ls) * 0.38
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad)


# ═════════════════════════════════════════════════════════════════════════════
# TRAPEZIYA
# ═════════════════════════════════════════════════════════════════════════════


def draw_trapezoid(ax, items: dict, seed=42):
    """
    Trapeziya: parallel yuqori (top) va pastki (bottom) tomonlar.
    height — balandlik, left/right — yon tomonlar.
    """
    b = _parse_numeric(items.get("bottom", "8"), 8.0)
    t = _parse_numeric(items.get("top", "5"), 5.0)
    h = _parse_numeric(items.get("height", "4"), 4.0)

    mx = max(b, t, h, 0.1)
    sc = 5.5 / mx
    bs, ts, hs = b * sc, t * sc, h * sc

    off = (bs - ts) / 2
    # A=sol-past, B=o'ng-past, C=o'ng-yuqori, D=sol-yuqori
    pts = [[0.0, 0.0], [bs, 0.0], [bs - off, hs], [off, hs]]

    ax.add_patch(
        patches.Polygon(
            pts,
            closed=True,
            facecolor=_FILL["trapezoid"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )

    # To'g'ri burchak belgilari (agar trapeziya to'g'ri burchakli bo'lsa)
    if items.get("right_angles", "").lower() in ("true", "yes", "1"):
        _right_sq(ax, pts[0], pts[1], pts[3], sz=hs * 0.10)
        _right_sq(ax, pts[1], pts[0], pts[2], sz=hs * 0.10)

    # Parallel tomon belgilari (>>)
    _ticks(ax, pts[0], pts[1], n=1)  # pastki parallel
    _ticks(ax, pts[3], pts[2], n=1)  # yuqori parallel

    # Vertex harflari
    ctr = _centroid(pts)
    for lbl, pt in zip(["A", "B", "C", "D"], pts):
        dx, dy = pt[0] - ctr[0], pt[1] - ctr[1]
        d = max(math.hypot(dx, dy), 1e-9)
        ax.text(
            pt[0] + dx / d * 0.50,
            pt[1] + dy / d * 0.50,
            lbl,
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
            zorder=5,
        )

    # Tomon labellar
    if "bottom" in items:
        ax.text(
            bs / 2,
            -0.45,
            items["bottom"],
            fontsize=_ls(items["bottom"]),
            color=_lc(items["bottom"]),
            fontweight="bold",
            ha="center",
        )
    if "top" in items:
        ax.text(
            off + ts / 2,
            hs + 0.38,
            items["top"],
            fontsize=_ls(items["top"]),
            color=_lc(items["top"]),
            fontweight="bold",
            ha="center",
        )
    if "left" in items:
        _side_lbl(ax, pts[0], pts[3], items["left"])
    if "right" in items:
        _side_lbl(ax, pts[1], pts[2], items["right"], side=-1)

    # Balandlik chiziq
    if "height" in items:
        mid_b = bs / 2
        ax.plot(
            [mid_b, mid_b],
            [0, hs],
            color=_AUX_CLR,
            linestyle="--",
            linewidth=1.5,
            zorder=1,
        )
        ax.text(
            mid_b + 0.28,
            hs / 2,
            items["height"],
            fontsize=_ls(items["height"]),
            color=_lc(items["height"]),
            fontweight="bold",
        )

    pad = max(bs, hs) * 0.28
    ax.set_xlim(-pad, bs + pad)
    ax.set_ylim(-pad * 1.5, hs + pad * 1.5)


# ═════════════════════════════════════════════════════════════════════════════
# ROMB
# ═════════════════════════════════════════════════════════════════════════════


def draw_rhombus(ax, items: dict, seed=42):
    """
    Romb: diagonal_1 (gorizontal), diagonal_2 (vertikal), side, angle_a.
    """
    d1 = _parse_numeric(items.get("diagonal_1", items.get("d1", "6")), 6.0)
    d2 = _parse_numeric(items.get("diagonal_2", items.get("d2", "4")), 4.0)

    mx = max(d1, d2, 0.1)
    sc = 4.8 / mx
    d1s, d2s = d1 * sc, d2 * sc

    # Romb nuqtalari: markazdan diagonallar
    cx, cy = d1s / 2, d2s / 2
    pts = [
        [cx, 0.0],  # pastki
        [d1s, cy],  # o'ng
        [cx, d2s],  # yuqori
        [0.0, cy],  # chap
    ]

    ax.add_patch(
        patches.Polygon(
            pts,
            closed=True,
            facecolor=_FILL["rhombus"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )

    # Diagonallar
    ax.plot([0.0, d1s], [cy, cy], color=_AUX_CLR, linestyle="--", lw=1.5, zorder=1)
    ax.plot([cx, cx], [0.0, d2s], color=_AUX_CLR, linestyle="--", lw=1.5, zorder=1)

    # Diagonal kesishish nuqtasi
    ax.plot(cx, cy, "o", color=_EDGE, markersize=4, zorder=4)

    # Teng tomonlar tick
    _ticks(ax, pts[0], pts[1], n=1)
    _ticks(ax, pts[1], pts[2], n=1)
    _ticks(ax, pts[2], pts[3], n=1)
    _ticks(ax, pts[3], pts[0], n=1)

    # Vertex harflari
    for lbl, pt in zip(["A", "B", "C", "D"], pts):
        off_x = 0.45 * (1 if pt[0] >= cx else -1)
        off_y = 0.45 * (1 if pt[1] >= cy else -1)
        ax.text(
            pt[0] + off_x,
            pt[1] + off_y,
            lbl,
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
        )

    # Diagonal labellar
    if "diagonal_1" in items or "d1" in items:
        v = items.get("diagonal_1", items.get("d1", ""))
        ax.text(
            d1s + 0.35,
            cy + 0.30,
            f"d₁={v}",
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
        )
    if "diagonal_2" in items or "d2" in items:
        v = items.get("diagonal_2", items.get("d2", ""))
        ax.text(
            cx + 0.20,
            d2s + 0.35,
            f"d₂={v}",
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
        )

    if "side" in items:
        _side_lbl(ax, pts[0], pts[1], items["side"])
    if "angle_a" in items:
        v = items["angle_a"]
        _angle_arc(ax, pts[3], pts[0], pts[2], r=0.38)
        ax.text(
            pts[3][0] - 0.55,
            pts[3][1],
            v,
            fontsize=_ls(v) - 2,
            color=_lc(v),
            fontweight="bold",
        )

    pad = 0.9
    ax.set_xlim(-pad, d1s + pad)
    ax.set_ylim(-pad, d2s + pad)


# ═════════════════════════════════════════════════════════════════════════════
# PARALLELOGRAMM
# ═════════════════════════════════════════════════════════════════════════════


def draw_parallelogram(ax, items: dict, seed=42):
    """
    Parallelogramm: bottom, left, angle_a (qiya burchak).
    """
    rng = _random.Random(seed)
    b = _parse_numeric(items.get("bottom", "7"), 7.0)
    l = _parse_numeric(items.get("left", "4"), 4.0)
    ang = _parse_numeric(items.get("angle_a", "60"), 60.0)

    mx = max(b, l, 0.1)
    sc = 5.2 / mx
    bs, ls = b * sc, l * sc

    ang_r = math.radians(ang)
    ox = ls * math.cos(ang_r)
    oy = ls * math.sin(ang_r)

    pts = [[0.0, 0.0], [bs, 0.0], [bs + ox, oy], [ox, oy]]

    ax.add_patch(
        patches.Polygon(
            pts,
            closed=True,
            facecolor=_FILL["parallelogram"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )

    # Parallel tomon tick
    _ticks(ax, pts[0], pts[1], n=2)
    _ticks(ax, pts[3], pts[2], n=2)
    _ticks(ax, pts[0], pts[3], n=1)
    _ticks(ax, pts[1], pts[2], n=1)

    # Vertex harflari
    for lbl, pt, (dx, dy) in zip(
        ["A", "B", "C", "D"], pts, [(-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)]
    ):
        ax.text(
            pt[0] + dx,
            pt[1] + dy,
            lbl,
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
        )

    if "bottom" in items:
        ax.text(
            bs / 2,
            -0.50,
            items["bottom"],
            fontsize=_ls(items["bottom"]),
            color=_lc(items["bottom"]),
            fontweight="bold",
            ha="center",
        )
    if "left" in items:
        _side_lbl(ax, pts[0], pts[3], items["left"])
    if "angle_a" in items:
        v = items["angle_a"]
        _angle_arc(ax, pts[0], pts[1], pts[3], r=0.40)
        ax.text(
            pts[0][0] + 0.55,
            pts[0][1] + 0.22,
            v,
            fontsize=_ls(v) - 2,
            color=_lc(v),
            fontweight="bold",
        )
    if "height" in items:
        mid_x = bs / 2
        ax.plot(
            [mid_x, mid_x], [0, oy], color=_AUX_CLR, linestyle="--", lw=1.5, zorder=1
        )
        ax.text(
            mid_x + 0.28,
            oy / 2,
            items["height"],
            fontsize=_ls(items["height"]),
            color=_lc(items["height"]),
            fontweight="bold",
        )

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = max(bs, oy) * 0.28
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad * 1.5, max(all_y) + pad * 1.5)


# ═════════════════════════════════════════════════════════════════════════════
# OLTIBURCHAK
# ═════════════════════════════════════════════════════════════════════════════


def draw_hexagon(ax, items: dict, seed=42):
    rng = _random.Random(seed)
    r = 2.5
    rot = rng.uniform(-10.0, 10.0)

    pts = [
        [
            r * math.cos(math.radians(60 * i + rot)),
            r * math.sin(math.radians(60 * i + rot)),
        ]
        for i in range(6)
    ]

    ax.add_patch(
        patches.Polygon(
            pts,
            closed=True,
            facecolor=_FILL["hexagon"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )

    for i, p in enumerate(pts):
        ax.text(
            p[0] * 1.18,
            p[1] * 1.18,
            "ABCDEF"[i],
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
        )

    if "side" in items or "tomon" in items:
        v = items.get("side", items.get("tomon", ""))
        mx = (pts[0][0] + pts[1][0]) / 2
        my = (pts[0][1] + pts[1][1]) / 2
        ax.text(
            mx * 1.14,
            my * 1.14,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
            va="center",
        )

    if "radius" in items:
        v = items["radius"]
        ax.plot([0, pts[0][0]], [0, pts[0][1]], color=_AUX_CLR, linestyle="--", lw=1.6)
        ax.text(
            pts[0][0] / 2,
            pts[0][1] / 2 - 0.3,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            style="italic",
            fontweight="bold",
            ha="center",
        )

    ax.set_xlim(-r * 1.55, r * 1.55)
    ax.set_ylim(-r * 1.55, r * 1.55)


# ═════════════════════════════════════════════════════════════════════════════
# TO'RTBURCHAK
# ═════════════════════════════════════════════════════════════════════════════


def draw_rectangle(ax, items: dict, seed=42):
    b = _parse_numeric(items.get("bottom", "6"), 6.0)
    l = _parse_numeric(items.get("left", "3"), 3.0)

    mx = max(b, l, 0.1)
    sc = 5.5 / mx
    w, h = b * sc, l * sc

    ax.add_patch(
        patches.Rectangle(
            (0, 0),
            w,
            h,
            facecolor=_FILL["rectangle"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )

    off = max(w, h) * 0.065
    sq = off * 0.7
    for cx, cy, sdx, sdy in [
        (0, 0, sq, sq),
        (w, 0, -sq, sq),
        (w, h, -sq, -sq),
        (0, h, sq, -sq),
    ]:
        ax.plot(
            [cx + sdx, cx + sdx, cx],
            [cy, cy + sdy, cy + sdy],
            color=_AUX_CLR,
            lw=1.3,
            zorder=3,
        )

    for lbl, (px, py) in zip(
        ["A", "B", "C", "D"],
        [
            (-off * 1.6, -off * 1.6),
            (w + off * 1.6, -off * 1.6),
            (w + off * 1.6, h + off * 1.6),
            (-off * 1.6, h + off * 1.6),
        ],
    ):
        ax.text(
            px,
            py,
            lbl,
            fontsize=12,
            fontweight="bold",
            color=_TXT_DARK,
            ha="center",
            va="center",
        )

    if "bottom" in items:
        v = items["bottom"]
        ax.text(
            w / 2,
            -off * 2.4,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
        )
    if "left" in items:
        v = items["left"]
        ax.text(
            -off * 3.2,
            h / 2,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
        )
    if "top" in items:
        v = items["top"]
        ax.text(
            w / 2,
            h + off * 2.4,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
        )
    if "right" in items:
        v = items["right"]
        ax.text(
            w + off * 3.2,
            h / 2,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
        )
    if "diagonal" in items:
        v = items["diagonal"]
        ax.plot([0, w], [0, h], color=_AUX_CLR, linestyle="--", lw=1.6, zorder=1)
        ax.text(
            w / 2 + off,
            h / 2 + off,
            v,
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="left",
            va="bottom",
        )
    if "area" in items:
        v = items["area"]
        ax.text(
            w / 2,
            h / 2,
            f"S = {v}",
            fontsize=_ls(v),
            color="#2563eb",
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bfdbfe", alpha=0.92),
        )

    pad = max(w, h) * 0.30
    ax.set_xlim(-pad, w + pad)
    ax.set_ylim(-pad, h + pad)


# ═════════════════════════════════════════════════════════════════════════════
# DOIRA / AYLANA
# ═════════════════════════════════════════════════════════════════════════════


def draw_circle(ax, items: dict, seed=42):
    r1r = items.get("radius_1", items.get("radius", "5"))
    r1 = _parse_numeric(r1r, 3.0)
    rs = 3.0  # ekranda standart radius
    label_box = dict(boxstyle="round,pad=0.18", fc="white", ec="#cbd5e1", alpha=0.96)

    ax.add_patch(
        patches.Circle(
            (0, 0),
            rs,
            facecolor=_FILL["circle"],
            edgecolor=_EDGE,
            linewidth=2.2,
            zorder=2,
        )
    )
    ax.plot(0, 0, "o", color=_EDGE, markersize=5, zorder=5)
    ax.text(
        -0.52,
        -0.54,
        "O",
        fontsize=12,
        fontweight="bold",
        color=_TXT_DARK,
        bbox=label_box,
        zorder=7,
    )

    if "radius_1" in items or "radius" in items:
        angle_1 = math.radians(-22)
        x1 = rs * math.cos(angle_1)
        y1 = rs * math.sin(angle_1)
        ax.plot([0, x1], [0, y1], color=_AUX_CLR, lw=1.8, zorder=3)
        ax.text(
            x1 * 0.48,
            y1 * 0.48 - 0.18,
            r1r,
            fontsize=_ls(r1r),
            color=_lc(r1r),
            style="italic",
            fontweight="bold",
            ha="center",
            va="center",
            bbox=label_box,
            zorder=7,
        )

    if "radius_2" in items:
        r2r = items["radius_2"]
        r2 = _parse_numeric(r2r, r1)
        r2s = min((r2 / max(r1, 1e-9)) * rs, rs)
        angle_2 = math.radians(58)
        x2 = r2s * math.cos(angle_2)
        y2 = r2s * math.sin(angle_2)
        ax.plot([0, x2], [0, y2], color=_AUX_CLR, lw=1.8, zorder=3)
        ax.text(
            x2 * 0.56 + 0.18,
            y2 * 0.56 + 0.12,
            r2r,
            fontsize=_ls(r2r),
            color=_lc(r2r),
            style="italic",
            fontweight="bold",
            ha="center",
            va="center",
            bbox=label_box,
            zorder=7,
        )

    if "diameter" in items:
        v = items["diameter"]
        ax.plot(
            [-rs * 0.92, rs * 0.92],
            [-rs * 0.18, rs * 0.18],
            color=_AUX_CLR,
            linestyle="--",
            lw=1.5,
            zorder=1,
        )
        ax.text(
            0,
            -rs * 0.72,
            f"d = {v}",
            fontsize=_ls(v),
            color=_lc(v),
            fontweight="bold",
            ha="center",
            bbox=label_box,
            zorder=7,
        )

    if "element" in items:
        ax.text(
            -rs * 0.9,
            rs * 0.82,
            items["element"],
            fontsize=15,
            color=_TXT_DARK,
            bbox=label_box,
            zorder=7,
        )
    if "center" in items:
        ax.text(
            0,
            -0.75,
            f"markaz: {items['center']}",
            fontsize=12,
            color=_AUX_CLR,
            ha="center",
            bbox=label_box,
            zorder=7,
        )

    pad = rs * 0.55
    ax.set_xlim(-rs - pad, rs + pad)
    ax.set_ylim(-rs - pad, rs + pad)


# ═════════════════════════════════════════════════════════════════════════════
# KOORDINAT TEKISLIK
# ═════════════════════════════════════════════════════════════════════════════


def draw_coordinate(ax, items: dict, seed=42):
    """
    Koordinat tekislik: nuqtalar, chiziqlar, to'g'ri chiziq.
    Kalitlar: x1,y1,x2,y2  (nuqtalar),
              slope, intercept  (to'g'ri chiziq y=kx+b),
              point1 "a,b", point2 "a,b"  (nuqta koordinatalar)
    """
    ax.axis("on")
    ax.set_aspect("equal")

    lim = 5
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    # O'qlar
    ax.axhline(0, color=_EDGE, lw=1.8, zorder=2)
    ax.axvline(0, color=_EDGE, lw=1.8, zorder=2)

    # O'q o'qchalari
    ax.annotate(
        "",
        xy=(lim, 0),
        xytext=(lim - 0.6, 0),
        arrowprops=dict(arrowstyle="->", color=_EDGE, lw=1.6),
    )
    ax.annotate(
        "",
        xy=(0, lim),
        xytext=(0, lim - 0.6),
        arrowprops=dict(arrowstyle="->", color=_EDGE, lw=1.6),
    )
    ax.text(lim + 0.15, 0.15, "x", fontsize=13, fontweight="bold", color=_EDGE)
    ax.text(0.15, lim + 0.15, "y", fontsize=13, fontweight="bold", color=_EDGE)

    # Katak (grid)
    for i in range(-lim + 1, lim):
        ax.axhline(i, color="#e2e8f0", lw=0.6, zorder=0)
        ax.axvline(i, color="#e2e8f0", lw=0.6, zorder=0)

    # O'q raqamlari
    for i in range(-lim + 1, lim):
        if i == 0:
            continue
        ax.text(i, -0.38, str(i), fontsize=8, color=_AUX_CLR, ha="center", va="center")
        ax.text(-0.38, i, str(i), fontsize=8, color=_AUX_CLR, ha="center", va="center")
    ax.text(-0.35, -0.35, "0", fontsize=9, color=_AUX_CLR, ha="center", va="center")

    colors_pts = ["#e11d48", "#2563eb", "#10b981", "#f59e0b"]

    # Nuqtalar (point1, point2, ...)
    for idx in range(1, 6):
        key = f"point{idx}"
        if key not in items:
            break
        raw = items[key]
        try:
            px, py_v = raw.split(",")
            px_f = _parse_numeric(px)
            py_f = _parse_numeric(py_v)
            is_unk = _is_unknown(px) or _is_unknown(py_v)
            clr = _UNK_CLR if is_unk else colors_pts[idx % len(colors_pts)]
            ax.plot(px_f, py_f, "o", color=clr, markersize=8, zorder=6)
            ax.text(
                px_f + 0.22,
                py_f + 0.25,
                f"({px.strip()}, {py_v.strip()})",
                fontsize=9,
                color=clr,
                fontweight="bold",
                zorder=6,
            )
        except Exception:
            pass

    # To'g'ri chiziq: y = kx + b
    if "slope" in items or "intercept" in items:
        k = _parse_numeric(items.get("slope", "1"), 1.0)
        b = _parse_numeric(items.get("intercept", "0"), 0.0)
        xs = [-lim, lim]
        ys = [k * x + b for x in xs]
        ax.plot(xs, ys, color="#2563eb", lw=2.0, zorder=3)
        # Chiziq belgisi
        k_txt = items.get("slope", "1")
        b_txt = items.get("intercept", "0")
        ax.text(
            lim - 0.5,
            k * lim + b + 0.3,
            f"y = {k_txt}x + {b_txt}",
            fontsize=10,
            color="#2563eb",
            fontweight="bold",
            ha="right",
        )

    # x1,y1 → x2,y2 segment
    if "x1" in items and "y1" in items and "x2" in items and "y2" in items:
        x1 = _parse_numeric(items["x1"])
        y1 = _parse_numeric(items["y1"])
        x2 = _parse_numeric(items["x2"])
        y2 = _parse_numeric(items["y2"])
        ax.plot([x1, x2], [y1, y2], color="#e11d48", lw=2.0, zorder=3)
        ax.plot([x1, x2], [y1, y2], "o", color="#e11d48", markersize=7, zorder=5)
        for px, py, lbl in [
            (x1, y1, f"({items['x1']},{items['y1']})"),
            (x2, y2, f"({items['x2']},{items['y2']})"),
        ]:
            ax.text(
                px + 0.2,
                py + 0.28,
                lbl,
                fontsize=9,
                color="#e11d48",
                fontweight="bold",
                zorder=6,
            )

    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)


# ═════════════════════════════════════════════════════════════════════════════
# SON O'QI (NUMBER LINE)
# ═════════════════════════════════════════════════════════════════════════════


def draw_number_line(ax, items: dict, seed=42):
    """
    Son o'qi: start, end, mark1..mark5, point (noma'lum joyi), label.
    """
    ax.axis("on")
    ax.set_aspect("auto")

    mn = int(_parse_numeric(items.get("start", "-5"), -5.0))
    mx = int(_parse_numeric(items.get("end", " 5"), 5.0))
    if mx <= mn:
        mx = mn + 10

    rng_w = mx - mn
    pad = rng_w * 0.15
    ax.set_xlim(mn - pad, mx + pad)
    ax.set_ylim(-2.2, 2.2)
    ax.axhline(0, color=_EDGE, lw=2.2, zorder=2)

    # O'q o'qchalari
    ax.annotate(
        "",
        xy=(mx + pad * 0.7, 0),
        xytext=(mx + pad * 0.3, 0),
        arrowprops=dict(arrowstyle="->", color=_EDGE, lw=1.8),
    )
    ax.annotate(
        "",
        xy=(mn - pad * 0.7, 0),
        xytext=(mn - pad * 0.3, 0),
        arrowprops=dict(arrowstyle="->", color=_EDGE, lw=1.8),
    )

    # Tirklar va raqamlar
    for i in range(mn, mx + 1):
        ax.plot([i, i], [-0.22, 0.22], color=_EDGE, lw=1.8, zorder=3)
        ax.text(i, -0.60, str(i), fontsize=11, color=_TXT_DARK, ha="center", va="top")

    # Belgilangan nuqtalar
    pt_colors = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]
    for idx in range(1, 6):
        key = f"mark{idx}"
        if key not in items:
            continue
        raw = items[key]
        xv = _parse_numeric(raw, 0.0)
        is_unk = _is_unknown(raw)
        clr = _UNK_CLR if is_unk else pt_colors[idx % len(pt_colors)]
        ax.plot(xv, 0, "o", color=clr, markersize=11, zorder=5)
        ax.text(
            xv, 0.70, raw, fontsize=_ls(raw), color=clr, fontweight="bold", ha="center"
        )

    # Noma'lum nuqta (x)
    if "point" in items:
        raw = items["point"]
        xv = _parse_numeric(raw, (mn + mx) / 2)
        ax.plot(xv, 0, "o", color=_UNK_CLR, markersize=13, zorder=6)
        ax.text(
            xv, 0.88, raw, fontsize=18, color=_UNK_CLR, fontweight="bold", ha="center"
        )

    # Interval (agar from-to bo'lsa)
    if "from" in items and "to" in items:
        f_ = _parse_numeric(items["from"])
        t_ = _parse_numeric(items["to"])
        ax.fill_betweenx([-0.18, 0.18], f_, t_, color="#bfdbfe", alpha=0.7, zorder=1)

    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)


# ═════════════════════════════════════════════════════════════════════════════
# USTUNLI DIAGRAMMA (BAR CHART)
# ═════════════════════════════════════════════════════════════════════════════


def draw_bar_chart(ax, items: dict, seed=42):
    """
    Ustunli diagramma.
    Kalitlar: bar1..bar7, label1..label7, title, ymax.
    Noma'lum (x) ustun — qizil va ta'kidlangan.
    """
    ax.axis("on")
    ax.set_aspect("auto")

    vals: list = []
    labels: list = []
    unkn: list = []

    for i in range(1, 8):
        k = f"bar{i}"
        if k not in items:
            break
        raw = items[k]
        is_unk = _is_unknown(raw)
        vals.append(_parse_numeric(raw, 10.0) if not is_unk else 0.0)
        unkn.append(is_unk)
        labels.append(items.get(f"label{i}", f"#{i}"))

    if not vals:
        # fallback
        vals = [15, 22, 18, 30, 10]
        labels = ["A", "B", "C", "D", "E"]
        unkn = [False] * 5

    mx_v = (
        max(v for v, u in zip(vals, unkn) if not u) if any(not u for u in unkn) else 30
    )
    ymax = _parse_numeric(items.get("ymax", ""), mx_v * 1.35)

    x_pos = list(range(len(vals)))

    for i, (v, lbl, is_unk) in enumerate(zip(vals, labels, unkn)):
        clr = _UNK_CLR if is_unk else _BAR_COLORS[i % len(_BAR_COLORS)]
        bar_h = mx_v * 0.75 if is_unk else v
        bar = ax.bar(
            i,
            bar_h,
            color=clr,
            alpha=0.85 if not is_unk else 0.35,
            edgecolor="white",
            linewidth=1.2,
            width=0.65,
            zorder=3,
        )
        if is_unk:
            # Kesik chiziq efekti
            ax.bar(
                i,
                bar_h,
                fill=False,
                edgecolor=_UNK_CLR,
                linestyle="--",
                linewidth=2.0,
                width=0.65,
                zorder=4,
            )
            ax.text(
                i,
                bar_h + ymax * 0.03,
                "x",
                fontsize=18,
                color=_UNK_CLR,
                fontweight="bold",
                ha="center",
                va="bottom",
            )
        else:
            ax.text(
                i,
                v + ymax * 0.02,
                str(items.get(f"bar{i + 1}", v)),
                fontsize=11,
                color=_TXT_DARK,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold", color=_TXT_DARK)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_tick_params(labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, alpha=0.4, color="#e2e8f0", zorder=0)

    if "title" in items:
        ax.set_title(
            items["title"], fontsize=13, fontweight="bold", color=_TXT_DARK, pad=8
        )


# ═════════════════════════════════════════════════════════════════════════════
# DOIRA DIAGRAMMA (PIE CHART)
# ═════════════════════════════════════════════════════════════════════════════


def draw_pie_chart(ax, items: dict, seed=42):
    """
    Doira diagramma.
    Kalitlar: slice1..slice6, label1..label6.
    Noma'lum kesim x belgisi bilan ko'rsatiladi.
    """
    vals: list = []
    labels: list = []
    unkn: list = []
    unk_idx = -1

    for i in range(1, 7):
        k = f"slice{i}"
        if k not in items:
            break
        raw = items[k]
        is_unk = _is_unknown(raw)
        vals.append(_parse_numeric(raw, 25.0))
        labels.append(items.get(f"label{i}", f"{i}-qism"))
        unkn.append(is_unk)
        if is_unk:
            unk_idx = len(vals) - 1

    if not vals:
        vals = [30, 25, 20, 15, 10]
        labels = ["A", "B", "C", "D", "E"]
        unkn = [False] * 5

    # Noma'lum kesim: qolganlarni ayirib topamiz
    total_known = sum(v for v, u in zip(vals, unkn) if not u)
    if unk_idx >= 0:
        remaining = max(100.0 - total_known, 5.0)
        vals[unk_idx] = remaining

    colors = [
        (_UNK_CLR if u else _PIE_COLORS[i % len(_PIE_COLORS)])
        for i, (u) in enumerate(unkn)
    ]

    explode = [0.08 if u else 0.0 for u in unkn]

    wedges, texts, autotexts = ax.pie(
        vals,
        labels=None,
        colors=colors,
        explode=explode,
        autopct=lambda p: f"{p:.0f}%",
        startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=1.8),
        pctdistance=0.72,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
        at.set_color("white")

    # Legend
    legend_labels = []
    for lbl, v, u in zip(labels, vals, unkn):
        if u:
            legend_labels.append(f"{lbl} = x (noma'lum)")
        else:
            legend_labels.append(f"{lbl} = {v:.0f}%")

    ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=3,
        fontsize=9,
        frameon=False,
    )

    if "title" in items:
        ax.set_title(items["title"], fontsize=13, fontweight="bold", color=_TXT_DARK)


# ═════════════════════════════════════════════════════════════════════════════
# SOAT (CLOCK)
# ═════════════════════════════════════════════════════════════════════════════


def draw_clock(ax, items: dict, seed=42):
    """
    Soat yuzi: hour, minute, second (ixtiyoriy).
    Noma'lum soat yoki daqiqa belgisi ko'rsatiladi.
    """
    r = 3.0  # soat radiusi

    # Soat yuzi
    ax.add_patch(
        patches.Circle(
            (0, 0), r, facecolor="white", edgecolor=_EDGE, linewidth=3.0, zorder=2
        )
    )
    ax.add_patch(patches.Circle((0, 0), r * 0.04, facecolor=_EDGE, zorder=6))

    # Soat belgilari (1-12)
    for i in range(1, 13):
        ang = math.radians(90 - 30 * i)
        rx, ry = r * 0.82 * math.cos(ang), r * 0.82 * math.sin(ang)
        # Katta belgi
        tx, ty = r * 0.92 * math.cos(ang), r * 0.92 * math.sin(ang)
        ax.plot(
            [tx * 0.97, tx * 0.88],
            [ty * 0.97, ty * 0.88],
            color=_EDGE,
            lw=2.2 if i % 3 == 0 else 1.2,
            zorder=3,
        )
        if i % 3 == 0:
            ax.text(
                rx,
                ry,
                str(i),
                fontsize=11,
                fontweight="bold",
                color=_TXT_DARK,
                ha="center",
                va="center",
            )
        else:
            ax.text(
                rx, ry, str(i), fontsize=9, color=_AUX_CLR, ha="center", va="center"
            )

    # Daqiqa belgilari
    for i in range(60):
        if i % 5 == 0:
            continue
        ang = math.radians(90 - 6 * i)
        ax.plot(
            [r * 0.96 * math.cos(ang), r * 0.88 * math.cos(ang)],
            [r * 0.96 * math.sin(ang), r * 0.88 * math.sin(ang)],
            color="#cbd5e1",
            lw=0.8,
            zorder=2,
        )

    # Soat mili
    h_raw = items.get("hour", "12")
    m_raw = items.get("minute", "0")
    h_unk = _is_unknown(h_raw)
    m_unk = _is_unknown(m_raw)

    h_val = _parse_numeric(h_raw, 12.0) % 12
    m_val = _parse_numeric(m_raw, 0.0)

    # Soat mili (kalta)
    if not h_unk:
        h_ang = math.radians(90 - 30 * h_val - 0.5 * m_val)
        ax.annotate(
            "",
            xy=(r * 0.52 * math.cos(h_ang), r * 0.52 * math.sin(h_ang)),
            xytext=(0, 0),
            arrowprops=dict(arrowstyle="-|>", color=_EDGE, lw=3.5, mutation_scale=14),
        )
    else:
        ax.text(
            0,
            -0.15,
            "?",
            fontsize=30,
            color=_UNK_CLR,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=8,
        )

    # Daqiqa mili (uzun)
    if not m_unk:
        m_ang = math.radians(90 - 6 * m_val)
        ax.annotate(
            "",
            xy=(r * 0.78 * math.cos(m_ang), r * 0.78 * math.sin(m_ang)),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>", color="#475569", lw=2.2, mutation_scale=12
            ),
        )
    else:
        # Noma'lum daqiqa — qizil yoy bilan ko'rsatamiz
        ax.add_patch(
            Arc(
                (0, 0),
                r * 1.55,
                r * 1.55,
                angle=0,
                theta1=0,
                theta2=360,
                color=_UNK_CLR,
                linewidth=2.0,
                linestyle="--",
            )
        )
        ax.text(
            r * 0.85,
            r * 0.85,
            "? daqiqa",
            fontsize=11,
            color=_UNK_CLR,
            fontweight="bold",
        )

    # Ikkinchi mili (ixtiyoriy)
    if "second" in items:
        s_raw = items["second"]
        if not _is_unknown(s_raw):
            s_val = _parse_numeric(s_raw, 0.0)
            s_ang = math.radians(90 - 6 * s_val)
            ax.plot(
                [0, r * 0.88 * math.cos(s_ang)],
                [0, r * 0.88 * math.sin(s_ang)],
                color="#ef4444",
                lw=1.2,
                zorder=4,
            )

    # Soat matni
    if not (h_unk or m_unk):
        ax.text(
            0,
            -r * 0.55,
            f"{int(h_val):02d}:{int(m_val):02d}",
            fontsize=13,
            color=_TXT_DARK,
            fontweight="bold",
            ha="center",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#e2e8f0", alpha=0.85),
        )

    pad = r * 0.35
    ax.set_xlim(-r - pad, r + pad)
    ax.set_ylim(-r - pad, r + pad)


# ═════════════════════════════════════════════════════════════════════════════
# MANTIQIY JADVAL (GRID)
# ═════════════════════════════════════════════════════════════════════════════


def draw_logic_grid(ax, items: dict, seed=42):
    """
    3x3 mantiqiy jadval - sonli boshqotirma.
    Har bir katakchada son bor, bittasi noma'lum (x).
    """
    rows, cols, cs = 3, 3, 1.3
    cell_keys = [
        ["cell1", "cell2", "cell3"],
        ["cell4", "cell5", "cell6"],
        ["cell7", "cell8", "cell9"],
    ]
    start_x, start_y = 0.5, 0.5

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * cs
            y = start_y + (rows - 1 - row) * cs
            key = cell_keys[row][col]
            val = items.get(key, "")
            is_unk = _is_unknown(val) if val else False
            
            # Katakcha
            if is_unk:
                bg = "#fee2e2"
                ec = _UNK_CLR
                lw = 3
            else:
                bg = "#f0fdf4"
                ec = _EDGE
                lw = 2
                
            ax.add_patch(
                patches.FancyBboxPatch(
                    (x, y), cs, cs,
                    boxstyle="round,pad=0.02,rounding_size=0.08",
                    facecolor=bg,
                    edgecolor=ec,
                    linewidth=lw,
                    zorder=2,
                )
            )
            
            if val:
                ax.text(
                    x + cs / 2,
                    y + cs / 2,
                    val,
                    fontsize=18,
                    fontweight="bold",
                    color=_lc(val) if not is_unk else _UNK_CLR,
                    ha="center",
                    va="center",
                    zorder=5,
                )

    # Sarlavha
    ax.text(
        start_x + cols * cs / 2,
        start_y + rows * cs + 0.4,
        "Sonli boshqotirma",
        fontsize=12,
        fontweight="bold",
        color=_TXT_DARK,
        ha="center",
    )

    ax.set_xlim(0, start_x + cols * cs + 0.3)
    ax.set_ylim(0, start_y + rows * cs + 1.0)
    ax.axis("off")


# ═════════════════════════════════════════════════════════════════════════════
# TAROZI (SCALE)
# ═════════════════════════════════════════════════════════════════════════════


def draw_scale(ax, items: dict, seed=42):
    """
    Tarozi: chap tomon va o'ng tomon og'irliklari.
    Noma'lum qiymat x yoki ? belgisi bilan ko'rsatiladi.
    """
    lv_r = items.get("left_side", "")
    rv_r = items.get("right_side", "")
    lv = _parse_numeric(lv_r, 5.0) if lv_r and not _is_unknown(lv_r) else 5.0
    rv = _parse_numeric(rv_r, 5.0) if rv_r and not _is_unknown(rv_r) else 5.0

    diff = (lv - rv) / max(lv + rv, 1.0)
    tilt = max(min(diff * 25.0, 20.0), -20.0)

    # Tayanch (pastda)
    ax.add_patch(
        patches.FancyBboxPatch(
            (-0.8, -0.5), 1.6, 0.8,
            boxstyle="round,rounding_size=0.15",
            facecolor="#e2e8f0",
            edgecolor=_EDGE,
            linewidth=2,
            zorder=2,
        )
    )
    
    # Stol yuzasi
    ax.plot([-4, 4], [-0.5, -0.5], color=_EDGE, lw=3, zorder=1)
    
    # Vertikal tayoq
    tayoq_x = 0
    tayoq_y = -0.5
    tayoq_h = 3.5
    ax.plot([tayoq_x, tayoq_x], [tayoq_y, tayoq_y + tayoq_h], color=_EDGE, lw=4, zorder=2)
    
    # Aylanuvchi tayoq (sop)
    tilt_r = math.radians(tilt)
    arm_len = 2.8
    lx = tayoq_x - arm_len * math.cos(tilt_r)
    ly = tayoq_y + tayoq_h + arm_len * math.sin(tilt_r) * 0.3
    rx = tayoq_x + arm_len * math.cos(tilt_r)
    ry = tayoq_y + tayoq_h - arm_len * math.sin(tilt_r) * 0.3
    
    ax.plot([lx, rx], [ly, ry], color=_EDGE, lw=4, zorder=3)
    
    # Markaz sharcha
    cx = tayoq_x
    cy = tayoq_y + tayoq_h
    ax.plot(cx, cy, "o", color=_EDGE, markersize=8, zorder=5)
    
    # Chap palma
    is_unk_l = _is_unknown(lv_r)
    pal_bg_l = "#fee2e2" if is_unk_l else "#dbeafe"
    pal_ec_l = _UNK_CLR if is_unk_l else "#2563eb"
    
    ax.plot([lx, lx], [ly, ly - 0.8], color="#94a3b8", lw=2, zorder=3)
    ax.add_patch(
        patches.FancyBboxPatch(
            (lx - 0.6, ly - 1.2), 1.2, 0.5,
            boxstyle="round,rounding_size=0.1",
            facecolor=pal_bg_l,
            edgecolor=pal_ec_l,
            linewidth=2.5,
            zorder=4,
        )
    )
    ax.text(lx, ly - 0.95, lv_r if lv_r else "?", fontsize=18, fontweight="bold",
           color=pal_ec_l if is_unk_l else _TXT_DARK,
           ha="center", va="center", zorder=5)
    ax.text(lx, ly - 1.5, "Chap", fontsize=10, color="#64748b",
           ha="center", va="center")
    
    # O'ng palma
    is_unk_r = _is_unknown(rv_r)
    pal_bg_r = "#fee2e2" if is_unk_r else "#dcfce7"
    pal_ec_r = _UNK_CLR if is_unk_r else "#16a34a"
    
    ax.plot([rx, rx], [ry, ry - 0.8], color="#94a3b8", lw=2, zorder=3)
    ax.add_patch(
        patches.FancyBboxPatch(
            (rx - 0.6, ry - 1.2), 1.2, 0.5,
            boxstyle="round,rounding_size=0.1",
            facecolor=pal_bg_r,
            edgecolor=pal_ec_r,
            linewidth=2.5,
            zorder=4,
        )
    )
    ax.text(rx, ry - 0.95, rv_r if rv_r else "?", fontsize=18, fontweight="bold",
           color=pal_ec_r if is_unk_r else _TXT_DARK,
           ha="center", va="center", zorder=5)
    ax.text(rx, ry - 1.5, "O'ng", fontsize=10, color="#64748b",
           ha="center", va="center")
    
    # Sarlavha
    ax.text(0, tayoq_y + tayoq_h + 0.5, "Tarozi boshqotirmasi", fontsize=12,
           fontweight="bold", color=_TXT_DARK, ha="center")
    
    ax.set_xlim(-5, 5)
    ax.set_ylim(-1.5, 4.5)
    ax.axis("off")


# ═════════════════════════════════════════════════════════════════════════════
# KROSSVORD
# ═════════════════════════════════════════════════════════════════════════════


def draw_crossword(ax, items: dict, seed=42):
    """
    Sonli krossvord - 5 ta katakcha, bittasi noma'lum.
    """
    # 5 ta katakcha + 2 ta "qora" katak (to'ldirilmagan)
    cell_size = 1.0
    cells = [
        (0, 0, "cell1"),
        (1, 1, "cell2"),
        (1, 0, "cell3"),
        (1, -1, "cell4"),
        (2, 0, "cell5"),
    ]
    
    # Offset - markazga yaqinlashtirish
    min_x = min(c[0] for c in cells)
    min_y = min(c[1] for c in cells)
    
    for x_off, y_off, key in cells:
        x = (x_off - min_x) * cell_size + 0.5
        y = (y_off - min_y) * cell_size + 0.5
        val = items.get(key, "")
        is_unk = _is_unknown(val)
        
        if is_unk:
            bg = "#fee2e2"
            ec = _UNK_CLR
        else:
            bg = "white"
            ec = _EDGE
            
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y), cell_size, cell_size,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor=bg,
                edgecolor=ec,
                linewidth=2.5,
                zorder=2,
            )
        )
        
        if val:
            ax.text(
                x + cell_size / 2,
                y + cell_size / 2,
                val,
                fontsize=20,
                fontweight="bold",
                color=_UNK_CLR if is_unk else _TXT_DARK,
                ha="center",
                va="center",
                zorder=5,
            )
    
    # Sarlavha
    cols = max(c[0] for c in cells) - min_x + 1
    rows = max(c[1] for c in cells) - min_y + 1
    ax.text(
        (cols * cell_size) / 2 + 0.5,
        rows * cell_size + 1.0,
        "Sonli krossvord",
        fontsize=12,
        fontweight="bold",
        color=_TXT_DARK,
        ha="center",
    )
    
    ax.set_xlim(0, cols * cell_size + 1.5)
    ax.set_ylim(-0.5, rows * cell_size + 1.5)
    ax.axis("off")


# ═════════════════════════════════════════════════════════════════════════════
# LABIRINT
# ═════════════════════════════════════════════════════════════════════════════


def draw_labyrinth(ax, items: dict, seed=42):
    """
    Labirint - 5x5 jadval, kirish va chiqish belgilangan.
    Yo'ldagi son noma'lum bo'lishi mumkin.
    """
    rng = _random.Random(seed)
    SIZE = 4
    
    # Background
    ax.add_patch(
        patches.FancyBboxPatch(
            (0, 0), SIZE, SIZE,
            boxstyle="round,rounding_size=0.1",
            facecolor="#f8fafc",
            edgecolor=_EDGE,
            linewidth=3,
            zorder=1,
        )
    )
    
    # Katakcha grid
    for i in range(1, SIZE):
        ax.plot([i, i], [0, SIZE], color="#cbd5e1", lw=1, zorder=2)
        ax.plot([0, SIZE], [i, i], color="#cbd5e1", lw=1, zorder=2)
    
    # Kirish (chap pastda)
    start_lbl = items.get("start", "1")
    ax.add_patch(
        patches.FancyBboxPatch(
            (0.1, 0.1), 0.8, 0.8,
            boxstyle="round,rounding_size=0.2",
            facecolor="#dbeafe",
            edgecolor="#2563eb",
            linewidth=2,
            zorder=3,
        )
    )
    ax.text(0.5, 0.5, start_lbl, fontsize=16, fontweight="bold",
           color="#2563eb", ha="center", va="center", zorder=4)
    ax.text(-0.3, 0.5, "KIRISH", fontsize=9, color="#2563eb",
           ha="center", va="center", fontweight="bold", rotation=90)
    
    # Chiqish (o'ng yuqorida)
    end_lbl = items.get("end", "9")
    ax.add_patch(
        patches.FancyBboxPatch(
            (SIZE - 0.9, SIZE - 0.9), 0.8, 0.8,
            boxstyle="round,rounding_size=0.2",
            facecolor="#dcfce7",
            edgecolor="#16a34a",
            linewidth=2,
            zorder=3,
        )
    )
    ax.text(SIZE - 0.5, SIZE - 0.5, end_lbl, fontsize=16, fontweight="bold",
           color="#16a34a", ha="center", va="center", zorder=4)
    ax.text(SIZE + 0.4, SIZE - 0.5, "CHIQISH", fontsize=9, color="#16a34a",
           ha="center", va="center", fontweight="bold", rotation=270)
    
    # Yo'l qiymatlari
    val1 = items.get("path1", "")
    val2 = items.get("path2", "")
    val3 = items.get("path3", "")
    
    # Birinchi qiymat - o'rtada
    if val1:
        is_unk1 = _is_unknown(val1)
        bg1 = "#fee2e2" if is_unk1 else "#fef3c7"
        ax.add_patch(
            patches.FancyBboxPatch(
                (1.1, 1.1), 0.8, 0.8,
                boxstyle="round,rounding_size=0.15",
                facecolor=bg1,
                edgecolor=_UNK_CLR if is_unk1 else "#ca8a04",
                linewidth=2,
                zorder=3,
            )
        )
        ax.text(1.5, 1.5, val1, fontsize=16, fontweight="bold",
               color=_UNK_CLR if is_unk1 else _TXT_DARK,
               ha="center", va="center", zorder=4)
    
    # Ikkinchi qiymat
    if val2:
        is_unk2 = _is_unknown(val2)
        bg2 = "#fee2e2" if is_unk2 else "#dbeafe"
        ax.add_patch(
            patches.FancyBboxPatch(
                (2.1, 2.1), 0.8, 0.8,
                boxstyle="round,rounding_size=0.15",
                facecolor=bg2,
                edgecolor=_UNK_CLR if is_unk2 else "#7c3aed",
                linewidth=2,
                zorder=3,
            )
        )
        ax.text(2.5, 2.5, val2, fontsize=16, fontweight="bold",
               color=_UNK_CLR if is_unk2 else _TXT_DARK,
               ha="center", va="center", zorder=4)
    
    # Sarlavha
    ax.text(SIZE / 2, -0.5, "Labirint boshqotirmasi", fontsize=12,
           fontweight="bold", color=_TXT_DARK, ha="center")
    
    ax.set_xlim(-1, SIZE + 1)
    ax.set_ylim(-1, SIZE + 0.5)
    ax.axis("off")


# ═════════════════════════════════════════════════════════════════════════════
# MUHIM NUQTALAR — Uchburchakning ajoyib nuqtalari
# ═════════════════════════════════════════════════════════════════════════════


def _triangle_pts(bottom="6", left="4", right="5"):
    b = _parse_numeric(bottom, 6.0)
    l = _parse_numeric(left, 4.0)
    r = _parse_numeric(right, 5.0)
    mx = max(b, l, r, 0.1)
    sc = 5.0 / mx
    pts = [[0.0, 0.0], [b * sc, 0.0]]
    cx2 = l * sc
    cy2 = l * sc
    a1, a2 = 48.0, 56.0
    if a1 + a2 >= 174:
        a1, a2 = 58.0, 64.0
    cx2 = l * sc * math.cos(math.radians(a1))
    cy2 = l * sc * math.sin(math.radians(a1))
    pts.append([cx2, cy2])
    return pts, sc


def draw_triangle_centers(ax, items: dict, seed=42):
    """
    Uchburchakning ajoyib nuqtalari:
    - incenter: bissektrisalar kesishgan nuqta
    - circumcenter: tashqi chizilgan aylana markazi
    - centroid: medianalar kesishgan nuqta
    - orthocenter: balandliklar kesishgan nuqta
    """
    b = items.get("bottom", "6")
    l = items.get("left", "5")
    r = items.get("right", "7")
    center_type = items.get("center_type", "all")  # incenter, circumcenter, centroid, orthocenter, all

    pts, sc = _triangle_pts(b, l, r)

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(
            pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2
        )
    )

    ctr = _centroid(pts)

    if center_type in ("incenter", "all"):
        # Inmarkaz: bissektrisalar kesishgan nuqta
        # Burchak bissektrisalari uchun simple approximation
        a, b_pt, c = pts[0], pts[1], pts[2]
        ax.plot([ctr[0]], [ctr[1]], "o", color="#16a34a", markersize=12, zorder=6)
        ax.text(ctr[0] + 0.3, ctr[1] + 0.3, "I", fontsize=14, fontweight="bold", color="#16a34a")

    if center_type in ("circumcenter", "all"):
        # Sirkummarkaz: tomonlar o'rtalariga o'tkazilgan perpendikulyarlar kesishgan nuqta
        mids = [
            [(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2],
            [(pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2],
            [(pts[0][0] + pts[2][0]) / 2, (pts[0][1] + pts[2][1]) / 2],
        ]
        # Aylana markazini hisoblash
        m1, m2, m3 = mids
        d1 = _dist(m1, m2)
        d2 = _dist(m2, m3)
        circ_cx = (m1[0] + m2[0] + m3[0]) / 3
        circ_cy = (m1[1] + m2[1] + m3[1]) / 3

        # Tashqi aylana
        r_circ = _dist([circ_cx, circ_cy], pts[0])
        ax.add_patch(
            patches.Circle(
                (circ_cx, circ_cy), r_circ,
                fill=False, edgecolor="#7c3aed", linewidth=2.0, linestyle="--", zorder=3
            )
        )
        ax.plot([circ_cx], [circ_cy], "s", color="#7c3aed", markersize=10, zorder=6)
        ax.text(circ_cx + 0.3, circ_cy + 0.3, "O", fontsize=14, fontweight="bold", color="#7c3aed")

    if center_type in ("centroid", "all"):
        # Sentroid: medianalar kesishgan nuqta
        # Har bir uchdan qarama-qarshi tomon o'rtasiga chiziq
        for i in range(3):
            p = pts[i]
            opp_mid = [(pts[(i + 1) % 3][0] + pts[(i + 2) % 3][0]) / 2,
                      (pts[(i + 1) % 3][1] + pts[(i + 2) % 3][1]) / 2]
            ax.plot([p[0], opp_mid[0]], [p[1], opp_mid[1]], color="#2563eb", lw=1.5, linestyle=":", zorder=1)

        ax.plot([ctr[0]], [ctr[1]], "*", color="#2563eb", markersize=16, zorder=6)
        ax.text(ctr[0] + 0.3, ctr[1] + 0.3, "G", fontsize=14, fontweight="bold", color="#2563eb")

    if center_type in ("orthocenter", "all"):
        # Ortomarkaz: balandliklar kesishgan nuqta
        def _altitude(p_idx):
            p = pts[p_idx]
            p1 = pts[(p_idx + 1) % 3]
            p2 = pts[(p_idx + 2) % 3]
            ux, uy = _unit(p1, p2)
            nx, ny = _perp(ux, uy)
            # Perpendikulyar chiziq - qarama-qarshi tomonga
            t = -(p[0] * nx + p[1] * ny) / (ux * ny - uy * nx) if abs(ux * ny - uy * nx) > 1e-9 else 0
            foot_x = p[0] + ux * t
            foot_y = p[1] + uy * t
            ax.plot([p[0], foot_x], [p[1], foot_y], color="#dc2626", lw=1.5, linestyle="--", zorder=1)
            ax.plot([foot_x], [foot_y], "o", color="#dc2626", markersize=5, zorder=3)
            return [foot_x, foot_y]

        orth_x = (pts[0][0] + pts[1][0] + pts[2][0]) / 3
        orth_y = (pts[0][1] + pts[1][1] + pts[2][1]) / 3
        ax.plot([orth_x], [orth_y], "D", color="#dc2626", markersize=10, zorder=6)
        ax.text(orth_x + 0.3, orth_y + 0.3, "H", fontsize=14, fontweight="bold", color="#dc2626")

    # Vertex harflari
    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(
            pt[0] + dx / d * 0.55,
            pt[1] + dy / d * 0.55,
            lbl, fontsize=12, fontweight="bold", color=_TXT_DARK,
            ha="center", va="center", zorder=5
        )

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = 1.5
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

    # Legend
    if center_type == "all":
        legend_items = [
            ("I", "#16a34a", "Inmarkaz"),
            ("O", "#7c3aed", "Sirkummarkaz"),
            ("G", "#2563eb", "Sentroid"),
            ("H", "#dc2626", "Ortomarkaz"),
        ]
        for i, (lbl, clr, name) in enumerate(legend_items):
            ax.text(0.02, 0.98 - i * 0.08, f"{lbl} — {name}", fontsize=9,
                   color=clr, fontweight="bold", transform=ax.transAxes,
                   va="top", ha="left", bbox=dict(boxstyle="round", fc="white", ec=clr, alpha=0.8))


# ═════════════════════════════════════════════════════════════════════════════
# CHEVA TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_ceva_theorem(ax, items: dict, seed=42):
    """
    Cheva teoremasi: Uchburchak ichidagi nuqtadan uchlarga chiziqlar
    (AD, BE, CF) kesmalar nisbatlarining ko'paytmasi 1 ga teng.
    """
    pts = [[1.0, 0.5], [5.0, 0.5], [3.0, 4.5]]
    ctr = _centroid(pts)

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2)
    )

    # Ichki nuqta (通常 centroid yoki ichida)
    inner = [(pts[0][0] + pts[1][0] + pts[2][0]) / 3, (pts[0][1] + pts[1][1] + pts[2][1]) / 3]

    # AD, BE, CF chiziqlari
    ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], color=_EDGE, lw=1.5, zorder=3)
    ax.plot([pts[1][0], pts[2][0]], [pts[1][1], pts[2][1]], color=_EDGE, lw=1.5, zorder=3)
    ax.plot([pts[2][0], pts[0][0]], [pts[2][1], pts[0][1]], color=_EDGE, lw=1.5, zorder=3)

    for i, p in enumerate(pts):
        ax.plot([inner[0], p[0]], [inner[1], p[1]], color="#2563eb", lw=2.0, zorder=4)

    # Kesishish nuqtalari tomonlarda (D, E, F)
    def _intersection(p1, p2, p3, t=0.3):
        return [p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t]

    d_pt = _intersection(pts[1], pts[2], pts[0], 0.35)
    e_pt = _intersection(pts[0], pts[2], pts[1], 0.4)
    f_pt = _intersection(pts[0], pts[1], pts[2], 0.45)

    # Labelelar
    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(pt[0] + dx / d * 0.5, pt[1] + dy / d * 0.5, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    for lbl, pt in zip(["D", "E", "F"], [d_pt, e_pt, f_pt]):
        ax.text(pt[0], pt[1] - 0.25, lbl, fontsize=10, fontweight="bold", color="#2563eb", ha="center")

    ax.plot([inner[0]], [inner[1]], "o", color="#e11d48", markersize=10, zorder=6)
    ax.text(inner[0] + 0.2, inner[1] + 0.15, "P", fontsize=12, fontweight="bold", color="#e11d48")

    # Formula
    formula = "Cheva: (BD/DC) × (CE/EA) × (AF/FB) = 1"
    ax.text(3.0, -0.6, formula, fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#fef3c7", ec="#f59e0b", alpha=0.9))

    ax.set_xlim(0, 6)
    ax.set_ylim(-1.2, 5.5)


# ═════════════════════════════════════════════════════════════════════════════
# MENELAY TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_menelaus_theorem(ax, items: dict, seed=42):
    """
    Menelay teoremasi: To'g'ri chiziq uchburchak tomonlarini kesib o'tganda
    kesmalar nisbatlarining ko'paytmasi -1 ga teng.
    """
    pts = [[1.5, 1.0], [5.5, 1.0], [3.5, 4.5]]
    ctr = _centroid(pts)

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2)
    )

    # Kesuvchi to'g'ri chiziq
    x_min, x_max = 0, 7
    m = 0.5
    b_line = 0.5
    ax.plot([x_min, x_max], [m * x_min + b_line, m * x_max + b_line],
           color="#dc2626", lw=2.5, zorder=3)

    # Kesishish nuqtalari
    def _line_y(x):
        return m * x + b_line

    def _segment_intersection(p1, p2):
        if abs(p2[1] - p1[1]) < 1e-9:
            return None
        t = (_line_y(p1[0]) - p1[1]) / (p2[1] - p1[1])
        if 0 <= t <= 1:
            return [p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])]
        return None

    intersections = []
    labels_pos = []
    for i in range(3):
        ip = _segment_intersection(pts[i], pts[(i + 1) % 3])
        if ip:
            intersections.append((ip, chr(88 + i)))  # X, Y, Z

    for ip, lbl in intersections:
        ax.plot([ip[0]], [ip[1]], "o", color="#dc2626", markersize=10, zorder=5)
        offset = 0.3 if ip[1] > _line_y(ip[0] - 0.3) else -0.35
        ax.text(ip[0], ip[1] + offset, lbl, fontsize=11, fontweight="bold", color="#dc2626", ha="center")

    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(pt[0] + dx / d * 0.45, pt[1] + dy / d * 0.45, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    formula = "Menelay: (AX/XB) × (BY/YC) × (CZ/ZA) = −1"
    ax.text(3.5, -0.7, formula, fontsize=11, fontweight="bold", color="#dc2626", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#fee2e2", ec="#dc2626", alpha=0.9))

    ax.set_xlim(0, 7)
    ax.set_ylim(-1.3, 5.5)


# ═════════════════════════════════════════════════════════════════════════════
# STYUART TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_stewart_theorem(ax, items: dict, seed=42):
    """
    Styuart teoremasi: Uchburchakda ichidagi nuqtadan uchgacha bo'lgan kesma
    uzunligini topish formulasi.
    """
    a = _parse_numeric(items.get("side_a", "8"), 8.0)
    b = _parse_numeric(items.get("side_b", "6"), 6.0)
    c = _parse_numeric(items.get("side_c", "7"), 7.0)
    m = _parse_numeric(items.get("median", "4"), 4.0)
    x = items.get("ceva", "x")

    mx = max(a, b, c, 0.1)
    sc = 5.0 / mx
    as_, bs_, cs_ = a * sc, b * sc, c * sc

    pts = [[0.0, 0.0], [as_, 0.0]]
    cx2 = bs_ * (as_**2 + cs_**2 - bs_**2) / (2 * as_)
    cy2 = math.sqrt(max(cs_**2 - cx2**2, 0.01))
    pts.append([cx2, cy2])

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2)
    )

    ctr = _centroid(pts)

    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(pt[0] + dx / d * 0.55, pt[1] + dy / d * 0.55, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    # Mediana (A dan BC o'rtasiga)
    bc_mid = [(pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2]
    ax.plot([pts[0][0], bc_mid[0]], [pts[0][1], bc_mid[1]], color="#2563eb", lw=2.5, zorder=4)
    ax.plot([bc_mid[0]], [bc_mid[1]], "o", color="#2563eb", markersize=6, zorder=5)

    # Tomon labelelari
    ax.text(as_ / 2, -0.5, f"a={a}", fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text(bc_mid[0] + 0.3, bc_mid[1] - 0.35, f"m={m}", fontsize=11, fontweight="bold", color="#2563eb", ha="center")

    # Formula
    formula = "Styuart: b^2*m + c^2*n = a(d^2 + m*n)"
    ax.text(2.5, -1.5, "Styuart Teoremasi", fontsize=12, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#f3e8ff", ec="#7c3aed", alpha=0.9))
    ax.text(2.5, -2.2, formula, fontsize=10, fontweight="bold", color="#2563eb", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dbeafe", ec="#2563eb", alpha=0.9))

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = 1.2
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad * 1.5, max(all_y) + pad)


# ═════════════════════════════════════════════════════════════════════════════
# PTOLEMEY TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_ptolemy_theorem(ax, items: dict, seed=42):
    """
    Ptolemey teoremasi: Aylana ichiga chizilgan to'rtburchakda
    diagonallar uzunliklari ko'paytmasi = qarama-qarshi tomonlar
    ko'paytmalari yig'indisiga teng.
    """
    # Ketma-ket uchburchak (doira ichida)
    cx, cy, r = 3.5, 3.0, 2.8

    # Aylanaga chizilgan to'rtburchak uchlari
    angles = [20, 100, 175, 290]
    pts = []
    for a in angles:
        pts.append([cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))])

    fill = "#f0fdf4"
    for i in range(4):
        ax.add_patch(
            patches.Polygon([pts[i], pts[(i+1)%4]], closed=True,
                          facecolor=fill, edgecolor=_EDGE, linewidth=1.5, zorder=2)
        )

    # To'rtburchak
    for i in range(4):
        p1, p2 = pts[i], pts[(i+1)%4]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=_EDGE, lw=2.2, zorder=3)

    # Diagonallar
    ax.plot([pts[0][0], pts[2][0]], [pts[0][1], pts[2][1]], color="#e11d48", lw=2.5, linestyle="--", zorder=4)
    ax.plot([pts[1][0], pts[3][0]], [pts[1][1], pts[3][1]], color="#e11d48", lw=2.5, linestyle="--", zorder=4)

    # Aylana
    ax.add_patch(
        patches.Circle((cx, cy), r, fill=False, edgecolor="#7c3aed", linewidth=2.0, zorder=1)
    )

    # Vertex harflari
    for i, lbl in enumerate(["A", "B", "C", "D"]):
        ax.text(pts[i][0], pts[i][1] + 0.35, lbl, fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center")

    # Tomon labelelari
    mid_01 = [(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2]
    ax.text(mid_01[0], mid_01[1] - 0.3, "a", fontsize=10, fontweight="bold", color=_TXT_DARK, ha="center")

    # Formula
    formula = "Ptolemey: AC × BD = AB × CD + BC × AD"
    ax.text(3.5, 0.2, formula, fontsize=12, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.4", fc="#f3e8ff", ec="#7c3aed", alpha=0.95))

    ax.set_xlim(0, 7)
    ax.set_ylim(0, 6.5)


# ═════════════════════════════════════════════════════════════════════════════
# VARINYON TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_varignon_theorem(ax, items: dict, seed=42):
    """
    Varinyon teoremasi: Ixtiyoriy to'rtburchak tomonlari o'rtalarini
    tutashtirganda parallelogramm hosil bo'ladi.
    """
    # Ixtiyoriy to'rtburchak
    pts = [[1.0, 1.5], [5.5, 0.8], [4.5, 4.2], [1.8, 3.8]]

    # Asl to'rtburchak
    for i in range(4):
        p1, p2 = pts[i], pts[(i+1)%4]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=_EDGE, lw=2.5, zorder=3)

    fill = _FILL["rectangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.5, zorder=2)
    )

    # Tomonlar o'rtalari
    mids = [
        [(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2],
        [(pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2],
        [(pts[2][0] + pts[3][0]) / 2, (pts[2][1] + pts[3][1]) / 2],
        [(pts[3][0] + pts[0][0]) / 2, (pts[3][1] + pts[0][1]) / 2],
    ]

    # Varinyon parallelogrammasi
    fill_p = "#dbeafe"
    ax.add_patch(
        patches.Polygon(mids, closed=True, facecolor=fill_p, edgecolor="#2563eb", linewidth=3.0, zorder=4)
    )

    # O'rtalarni tutashtiruvchi chiziqlar
    for i in range(4):
        ax.plot([mids[i][0], mids[(i+1)%4][0]], [mids[i][1], mids[(i+1)%4][1]],
               color="#2563eb", lw=2.0, zorder=5)

    # Vertex harflari
    for i, lbl in enumerate(["A", "B", "C", "D"]):
        off = 0.35
        dx = 0
        dy = 0
        ax.text(pts[i][0] + dx, pts[i][1] + dy, lbl, fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center")

    # O'rtalar labelelari
    for i, lbl in enumerate(["M", "N", "P", "Q"]):
        ax.text(mids[i][0], mids[i][1], lbl, fontsize=11, fontweight="bold", color="#2563eb", ha="center", va="center",
               bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="#2563eb"))

    # Formula
    formula = "Varinyon: MN || BC, NP || CD, ..."
    ax.text(3.0, 0.0, formula, fontsize=11, fontweight="bold", color="#2563eb", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dbeafe", ec="#2563eb", alpha=0.9))

    ax.set_xlim(0, 7)
    ax.set_ylim(-0.5, 5.5)


# ═════════════════════════════════════════════════════════════════════════════
# GOMOTETIYA VA O'XSHASHLIK
# ═════════════════════════════════════════════════════════════════════════════


def draw_homothety(ax, items: dict, seed=42):
    """
    Gomotetiya: Shakllarni markaz va koeffitsiyent bilan kattalashtrish/qisqartirish.
    """
    cx, cy = 3.0, 2.5
    k = _parse_numeric(items.get("scale", "2"), 2.0)  # koeffitsiyent

    # Asosiy shakl (uchburchak)
    orig_pts = [[2.0, 1.0], [4.5, 1.0], [3.0, 3.5]]

    # Gomotetik shakl
    hom_pts = [[cx + k * (p[0] - cx), cy + k * (p[1] - cy)] for p in orig_pts]

    # Asosiy shakl
    fill_orig = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(orig_pts, closed=True, facecolor=fill_orig, edgecolor=_EDGE, linewidth=2.2, zorder=2)
    )

    # Gomotetik shakl
    fill_hom = "#fee2e2"
    ax.add_patch(
        patches.Polygon(hom_pts, closed=True, facecolor=fill_hom, edgecolor="#e11d48", linewidth=2.2, zorder=3)
    )

    # Markaz
    ax.plot([cx], [cy], "o", color="#7c3aed", markersize=12, zorder=6)
    ax.text(cx + 0.25, cy, "O", fontsize=14, fontweight="bold", color="#7c3aed")

    # Chiziqlar (markazdan uchlarga)
    for p in orig_pts:
        ax.plot([cx, p[0]], [cy, p[1]], color="#94a3b8", lw=1.2, linestyle="--", zorder=1)

    # Koeffitsiyent
    formula = f"Gomotetiya: k = {k}"
    ax.text(3.0, 0.2, formula, fontsize=12, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#f3e8ff", ec="#7c3aed", alpha=0.9))

    ax.set_xlim(0, 8)
    ax.set_ylim(-0.5, 6.5)


# ═════════════════════════════════════════════════════════════════════════════
# VEKTORLAR USULI
# ═════════════════════════════════════════════════════════════════════════════


def draw_vector_geometry(ax, items: dict, seed=42):
    """
    Vektorlar usuli: Geometrik masalalarni vektorlar yordamida yechish.
    """
    origin = [1.0, 2.0]
    vec_a = [_parse_numeric(items.get("ax", "3"), 3.0), _parse_numeric(items.get("ay", "2"), 2.0)]
    vec_b = [_parse_numeric(items.get("bx", "2"), 2.0), _parse_numeric(items.get("by", "3.5"), 3.5)]

    ax.arrow(origin[0], origin[1], vec_a[0], vec_a[1], head_width=0.25, head_length=0.15,
            fc="#2563eb", ec="#2563eb", lw=2.5, zorder=4)
    ax.text(origin[0] + vec_a[0]/2 - 0.3, origin[1] + vec_a[1]/2, "→a", fontsize=12,
           fontweight="bold", color="#2563eb")

    ax.arrow(origin[0], origin[1], vec_b[0], vec_b[1], head_width=0.25, head_length=0.15,
            fc="#16a34a", ec="#16a34a", lw=2.5, zorder=4)
    ax.text(origin[0] + vec_b[0]/2 - 0.3, origin[1] + vec_b[1]/2, "→b", fontsize=12,
           fontweight="bold", color="#16a34a")

    # a + b
    end_ab = [origin[0] + vec_a[0] + vec_b[0], origin[1] + vec_a[1] + vec_b[1]]
    ax.arrow(origin[0], origin[1], end_ab[0] - origin[0], end_ab[1] - origin[1],
            head_width=0.2, head_length=0.12, fc="#e11d48", ec="#e11d48", lw=2.0, zorder=4)
    ax.text(end_ab[0] - 0.5, end_ab[1] + 0.25, "→a + →b", fontsize=11, fontweight="bold", color="#e11d48")

    # Origin
    ax.plot([origin[0]], [origin[1]], "o", color=_TXT_DARK, markersize=8, zorder=6)
    ax.text(origin[0] - 0.3, origin[1] - 0.35, "O", fontsize=12, fontweight="bold", color=_TXT_DARK)

    # Grid
    for i in range(-1, 7):
        ax.axhline(i, color="#e2e8f0", lw=0.5, zorder=0)
        ax.axvline(i, color="#e2e8f0", lw=0.5, zorder=0)

    # Formula
    formula = "→c = →a + →b"
    ax.text(3.5, 0.3, formula, fontsize=13, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.4", fc="#f3e8ff", ec="#7c3aed", alpha=0.95))

    ax.set_xlim(0, 7)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")


# ═════════════════════════════════════════════════════════════════════════════
# SINUSLAR VA KOSINUSLAR TEOREMASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_sin_cos_theorem(ax, items: dict, seed=42):
    """
    Sinuslar va Kosinuslar teoremalari.
    """
    b = _parse_numeric(items.get("side_a", "6"), 6.0)
    l = _parse_numeric(items.get("side_b", "5"), 5.0)
    ang = _parse_numeric(items.get("angle_c", "60"), 60.0)
    mx = max(b, l, 0.1)
    sc = 5.0 / mx
    bs, ls = b * sc, l * sc

    pts = [[0.0, 0.0], [bs, 0.0]]
    ang_r = math.radians(ang)
    pts.append([ls * math.cos(ang_r), ls * math.sin(ang_r)])

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.2, zorder=2)
    )

    ctr = _centroid(pts)

    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(pt[0] + dx / d * 0.55, pt[1] + dy / d * 0.55, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    # Burchak yoyi
    _angle_arc(ax, pts[0], pts[1], pts[2], r=0.5, color="#7c3aed")

    # Tomon labelelari
    ax.text(bs/2, -0.45, f"a = {b}", fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text(-0.6, ls * math.sin(ang_r) / 2, f"b = {l}", fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text((pts[2][0] + pts[1][0]) / 2 + 0.2, (pts[2][1] + pts[1][1]) / 2, f"c", fontsize=11, fontweight="bold", color=_TXT_DARK)

    # Formulas
    formula1 = f"Kosinuslar: c² = a² + b² − 2ab·cos(γ)"
    formula2 = f"Sinuslar: a/sin(α) = b/sin(β) = c/sin(γ)"
    ax.text(2.5, -1.5, formula1, fontsize=10, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#f3e8ff", ec="#7c3aed", alpha=0.9))
    ax.text(2.5, -2.2, formula2, fontsize=10, fontweight="bold", color="#2563eb", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dbeafe", ec="#2563eb", alpha=0.9))

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = 1.5
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad * 2, max(all_y) + pad)


# ═════════════════════════════════════════════════════════════════════════════
# ICHKI VA TASHQI CHIZILGAN TO'RTBURCHAKLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_circumscribed_quad(ax, items: dict, seed=42):
    """
    Tashqi chizilgan to'rtburchak: Qarama-qarshi tomonlar yig'indisi teng.
    (Ichki aylana chizish mumkin)
    """
    # Teng yonli trapetsiya (ichki aylana chizish mumkin)
    b1, b2 = 5.0, 2.5
    h = 3.0
    pts = [[0, 0], [b1, 0], [b1 - (b1 - b2)/2, h], [(b1 - b2)/2, h]]

    fill = _FILL["trapezoid"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.5, zorder=2)
    )

    # Ichki aylana
    r_in = h / 2
    cx_in = b1 / 2
    cy_in = h / 2
    ax.add_patch(
        patches.Circle((cx_in, cy_in), r_in, fill=False, edgecolor="#16a34a", linewidth=2.5, linestyle="--", zorder=3)
    )

    # Vertex harflari
    ctr = _centroid(pts)
    for i, lbl in enumerate(["A", "B", "C", "D"]):
        dx = pts[i][0] - ctr[0]
        dy = pts[i][1] - ctr[1]
        d = max(_dist(pts[i], ctr), 1e-9)
        ax.text(pts[i][0] + dx/d*0.5, pts[i][1] + dy/d*0.5, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    # Formula
    formula = "Tashqi chizilgan: AB + CD = BC + AD"
    ax.text(2.5, -0.6, formula, fontsize=11, fontweight="bold", color="#16a34a", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dcfce7", ec="#16a34a", alpha=0.9))

    ax.set_xlim(-1, 6.5)
    ax.set_ylim(-1.2, 4.5)


# ═════════════════════════════════════════════════════════════════════════════
# GERON FORMULASI
# ═════════════════════════════════════════════════════════════════════════════


def draw_heron_formula(ax, items: dict, seed=42):
    """
    Geron formulasi: Uchburchak yuzasini tomonlari bo'yicha hisoblash.
    S = √p(p-a)(p-b)(p-c), bunda p = (a+b+c)/2
    """
    b = _parse_numeric(items.get("side_a", "5"), 5.0)
    l = _parse_numeric(items.get("side_b", "4"), 4.0)
    c = _parse_numeric(items.get("side_c", "3"), 3.0)
    mx = max(b, l, c, 0.1)
    sc = 4.5 / mx
    bs, ls, cs = b * sc, l * sc, c * sc

    pts = [[0.0, 0.0], [bs, 0.0]]
    cx2 = (bs**2 + cs**2 - ls**2) / (2 * bs)
    cy2 = math.sqrt(max(cs**2 - cx2**2, 0.01))
    pts.append([cx2, cy2])

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.5, zorder=2)
    )

    ctr = _centroid(pts)

    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - ctr[0]
        dy = pt[1] - ctr[1]
        d = max(_dist(pt, ctr), 1e-9)
        ax.text(pt[0] + dx/d*0.6, pt[1] + dy/d*0.6, lbl,
               fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center", va="center")

    # Tomon labelelari
    ax.text(bs/2, -0.4, f"a={b}", fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text(-0.5, cy2/2, f"b={l}", fontsize=11, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text((pts[2][0] + pts[1][0])/2 + 0.2, (pts[2][1] + pts[1][1])/2, f"c={c}", fontsize=11, fontweight="bold", color=_TXT_DARK)

    # p = (a+b+c)/2
    p = (b + l + c) / 2
    s = math.sqrt(p * (p - b) * (p - l) * (p - c))

    # Formulas
    formula1 = f"Geron: p = (a+b+c)/2 = {p:.1f}"
    formula2 = f"S = √{p:.1f}×({p-b:.1f})×({p-l:.1f})×({p-c:.1f}) = {s:.1f}"
    ax.text(2.2, -1.3, formula1, fontsize=10, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#f3e8ff", ec="#7c3aed", alpha=0.9))
    ax.text(2.2, -2.0, formula2, fontsize=10, fontweight="bold", color="#2563eb", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dbeafe", ec="#2563eb", alpha=0.9))

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    pad = 1.5
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad * 2.5, max(all_y) + pad)


# ═════════════════════════════════════════════════════════════════════════════
# GIPOTENUZA VA KATETLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_pythagoras_detailed(ax, items: dict, seed=42):
    """
    Pifagor teoremasi: To'g'ri burchakli uchburchakda
    a² + b² = c²
    """
    b = _parse_numeric(items.get("bottom", "3"), 3.0)
    l = _parse_numeric(items.get("left", "4"), 4.0)
    mx = max(b, l, 0.1)
    sc = 5.0 / mx
    bs, ls = b * sc, l * sc

    pts = [[0.0, 0.0], [bs, 0.0], [0.0, ls]]

    fill = _FILL["triangle"]
    ax.add_patch(
        patches.Polygon(pts, closed=True, facecolor=fill, edgecolor=_EDGE, linewidth=2.5, zorder=2)
    )

    # To'g'ri burchak belgisi
    _right_sq(ax, pts[0], pts[1], pts[2], sz=min(bs, ls) * 0.1)

    # Vertex harflari
    for lbl, pt in zip(["A", "B", "C"], pts):
        dx = pt[0] - bs/2
        dy = pt[1] - ls/2
        off = 0.5
        if pt == pts[0]:
            ax.text(pt[0] - 0.4, pt[1] - 0.3, lbl, fontsize=12, fontweight="bold", color=_TXT_DARK)
        elif pt == pts[1]:
            ax.text(pt[0] + 0.2, pt[1] - 0.3, lbl, fontsize=12, fontweight="bold", color=_TXT_DARK)
        else:
            ax.text(pt[0] - 0.4, pt[1] + 0.2, lbl, fontsize=12, fontweight="bold", color=_TXT_DARK)

    # Tomon labelelari
    ax.text(bs/2, -0.5, f"a = {b}", fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center")
    ax.text(-0.5, ls/2, f"b = {l}", fontsize=12, fontweight="bold", color=_TXT_DARK, ha="center")

    c = math.sqrt(b**2 + l**2)
    hyp_mid = [bs/2, ls/2]
    ax.text(hyp_mid[0] + 0.3, hyp_mid[1] + 0.3, f"c = {c:.1f}", fontsize=12, fontweight="bold", color="#e11d48")

    # Formulas
    formula1 = f"Pifagor: a² + b² = c²"
    formula2 = f"{b}² + {l}² = {c:.1f}²"
    formula3 = f"{b*b:.0f} + {l*l:.0f} = {c*c:.0f}"
    ax.text(2.5, -1.5, formula1, fontsize=13, fontweight="bold", color="#7c3aed", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#f3e8ff", ec="#7c3aed", alpha=0.9))
    ax.text(2.5, -2.2, formula2, fontsize=11, fontweight="bold", color="#2563eb", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dbeafe", ec="#2563eb", alpha=0.9))
    ax.text(2.5, -2.9, formula3, fontsize=11, fontweight="bold", color="#16a34a", ha="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="#dcfce7", ec="#16a34a", alpha=0.9))

    ax.set_xlim(-1, bs + 1)
    ax.set_ylim(-3.5, ls + 1)


# ═════════════════════════════════════════════════════════════════════════════
# 3D SHAKLLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_3d_cube(ax, items: dict, seed=42):
    """Kub - 3D ko'rinishda"""
    size = _parse_numeric(items.get("size", "2"), 2.0)
    
    s = size
    h = s * 0.7
    
    face = [
        [1, 1, 0],
        [1 + s, 1, 0],
        [1 + s, 1 + s, 0],
        [1, 1 + s, 0]
    ]
    side1 = [
        [1 + s, 1, 0],
        [1 + s + h, 1 - h * 0.5, 0],
        [1 + s + h, 1 + s - h * 0.5, 0],
        [1 + s, 1 + s, 0]
    ]
    side2 = [
        [1, 1 + s, 0],
        [1 + s, 1 + s, 0],
        [1 + s + h, 1 + s - h * 0.5, 0],
        [1 + h, 1 + s + h * 0.5, 0]
    ]
    
    ax.add_patch(patches.Polygon(face, closed=True, facecolor="#E3F2FD", edgecolor="#1565C0", linewidth=2))
    ax.add_patch(patches.Polygon(side1, closed=True, facecolor="#90CAF9", edgecolor="#1565C0", linewidth=2))
    ax.add_patch(patches.Polygon(side2, closed=True, facecolor="#BBDEFB", edgecolor="#1565C0", linewidth=2))
    
    ax.text(1 + s/2, 1 + s/2, f"Kub\na = {s}", fontsize=11, ha="center", va="center", fontweight="bold")
    ax.text(1 + s/2, -0.8, f"V = a³ = {s**3:.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))


def draw_3d_prism(ax, items: dict, seed=42):
    """To'g'ri burchakli prizma - 3D ko'rinishda"""
    a = _parse_numeric(items.get("a", "3"), 3.0)
    b = _parse_numeric(items.get("b", "2"), 2.0)
    h = _parse_numeric(items.get("h", "4"), 4.0)
    
    off_x, off_y = h * 0.6, -h * 0.3
    
    base_pts = [[0, 0], [a, 0], [a, b], [0, b]]
    top_pts = [[p[0] + off_x, p[1] + off_y] for p in base_pts]
    
    for i in range(4):
        ax.plot([base_pts[i][0], top_pts[i][0]], [base_pts[i][1], top_pts[i][1]], 
                color="#7B1FA2", linewidth=2)
    
    ax.add_patch(patches.Polygon(base_pts, closed=True, facecolor="#E1BEE7", edgecolor="#7B1FA2", linewidth=2))
    ax.add_patch(patches.Polygon(top_pts, closed=True, facecolor="#CE93D8", edgecolor="#7B1FA2", linewidth=2))
    
    ax.text(a/2, b/2, f"Prizma\na={a}, b={b}, h={h}", fontsize=10, ha="center", va="center", fontweight="bold")
    ax.text(a/2, -1.2, f"V = a × b × h = {a*b*h:.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))


def draw_3d_pyramid(ax, items: dict, seed=42):
    """Piramida - 3D ko'rinishda"""
    a = _parse_numeric(items.get("a", "3"), 3.0)
    h = _parse_numeric(items.get("h", "4"), 4.0)
    
    center = [3, 0]
    top = [3 + h * 0.4, h * 0.7]
    
    base_pts = [
        [center[0] - a/2, center[1] - a/2],
        [center[0] + a/2, center[1] - a/2],
        [center[0] + a/2, center[1] + a/2],
        [center[0] - a/2, center[1] + a/2]
    ]
    
    ax.add_patch(patches.Polygon(base_pts, closed=True, facecolor="#FFF3E0", edgecolor="#E65100", linewidth=2))
    
    for pt in base_pts:
        ax.plot([top[0], pt[0]], [top[1], pt[1]], color="#E65100", linewidth=2)
    
    ax.text(center[0], center[1], f"Piramida\na={a}, h={h}", fontsize=10, ha="center", va="center", fontweight="bold")
    ax.text(center[0], center[1] - a/2 - 1, f"V = (1/3) × a² × h = {(a**2 * h / 3):.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))


def draw_3d_cylinder(ax, items: dict, seed=42):
    """Silindr - 3D ko'rinishda"""
    r = _parse_numeric(items.get("r", "2"), 2.0)
    h = _parse_numeric(items.get("h", "4"), 4.0)
    
    theta = np.linspace(np.pi/6, np.pi*5/6, 30)
    x = r * np.cos(theta) + 3
    y = r * np.sin(theta)
    
    ax.fill_between(x, y, -h, color="#E3F2FD", alpha=0.5)
    ax.plot(x, y, color="#1565C0", linewidth=2)
    ax.plot(x, y - h, color="#1565C0", linewidth=2)
    
    for i in range(0, len(x), 5):
        ax.plot([x[i], x[i]], [y[i], y[i] - h], color="#90CAF9", linewidth=1, alpha=0.5)
    
    ellipse_top = patches.Ellipse((3, 0), 2*r, r*0.3, facecolor="#BBDEFB", edgecolor="#1565C0", linewidth=2)
    ax.add_patch(ellipse_top)
    
    ax.text(3, -h/2, f"Silindr\nr={r}, h={h}", fontsize=10, ha="center", va="center", fontweight="bold")
    ax.text(3, -h - 1, f"V = πr²h = {3.14*r*r*h:.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))


def draw_3d_cone(ax, items: dict, seed=42):
    """Konus - 3D ko'rinishda"""
    r = _parse_numeric(items.get("r", "2"), 2.0)
    h = _parse_numeric(items.get("h", "4"), 4.0)
    
    center = [3, 0]
    top = [3, h]
    
    theta = np.linspace(np.pi/6, np.pi*5/6, 30)
    x = r * np.cos(theta) + center[0]
    y = r * np.sin(theta) + center[1]
    
    ax.fill_between(x, y, top[1], color="#FFF3E0", alpha=0.5)
    ax.plot(x, y, color="#E65100", linewidth=2)
    ax.plot([top[0], center[0]], [top[1], y[0]], color="#E65100", linewidth=2)
    ax.plot([top[0], x[-1]], [top[1], y[-1]], color="#E65100", linewidth=2)
    
    ellipse = patches.Ellipse((center[0], center[1]), 2*r, r*0.3, 
                               facecolor="#FFE0B2", edgecolor="#E65100", linewidth=2)
    ax.add_patch(ellipse)
    
    ax.text(center[0], h/2, f"Konus\nr={r}, h={h}", fontsize=10, ha="center", va="center", fontweight="bold")
    ax.text(center[0], -1.5, f"V = (1/3)πr²h = {(3.14*r*r*h/3):.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))


def draw_3d_sphere(ax, items: dict, seed=42):
    """Shar - 3D ko'rinishda (2D tasvir)"""
    r = _parse_numeric(items.get("r", "2"), 2.0)
    
    circle = patches.Circle((3, 3), r, facecolor="#E8F5E9", edgecolor="#2E7D32", linewidth=2)
    ax.add_patch(circle)
    
    for angle in np.linspace(0, 2*np.pi, 20):
        x1 = 3 + r * np.cos(angle)
        y1 = 3 + r * np.sin(angle)
        ax.plot([3, x1], [3, y1], color="#81C784", linewidth=0.5, alpha=0.3)
    
    circle_inner = patches.Circle((3, 3), r * 0.6, facecolor="none", edgecolor="#4CAF50", linewidth=1, linestyle="--")
    ax.add_patch(circle_inner)
    
    ax.text(3, 3, f"Shar\nr = {r}", fontsize=11, ha="center", va="center", fontweight="bold")
    ax.text(3, 3 - r - 1, f"V = (4/3)πr³ = {(4/3)*3.14*r**3:.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#4CAF50"))
    ax.text(3, 3 - r - 2, f"S = 4πr² = {4*3.14*r**2:.1f}", fontsize=10, ha="center",
           bbox=dict(boxstyle="round", fc="#E3F2FD", ec="#1565C0"))


# ═════════════════════════════════════════════════════════════════════════════
# FUNKSIYA GRAFLARI
# ═════════════════════════════════════════════════════════════════════════════


def draw_linear_function(ax, items: dict, seed=42):
    """Chiziqli funksiya: y = kx + b"""
    k = _parse_numeric(items.get("k", "2"), 2.0)
    b = _parse_numeric(items.get("b", "1"), 1.0)
    
    x = np.linspace(-5, 5, 100)
    y = k * x + b
    
    ax.plot(x, y, color="#E53935", linewidth=2.5, label=f"y = {k}x + {b}")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.scatter([0], [b], color="#E53935", s=50, zorder=5)
    ax.text(0.2, b + 0.3, f"(0, {b})", fontsize=10)
    
    if k != 0:
        x_intercept = -b / k
        ax.scatter([x_intercept], [0], color="#1E88E5", s=50, zorder=5)
        ax.text(x_intercept + 0.2, 0.3, f"({x_intercept:.1f}, 0)", fontsize=10)
    
    ax.set_xlim(-6, 6)
    ax.set_ylim(-6, 6)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")


def draw_quadratic_function(ax, items: dict, seed=42):
    """Kvadrat funksiya: y = ax² + bx + c"""
    a = _parse_numeric(items.get("a", "1"), 1.0)
    b = _parse_numeric(items.get("b", "-2"), -2.0)
    c = _parse_numeric(items.get("c", "0"), 0.0)
    
    x = np.linspace(-5, 5, 100)
    y = a * x**2 + b * x + c
    
    ax.plot(x, y, color="#7B1FA2", linewidth=2.5, label=f"y = {a}x² + {b}x + {c}")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    vertex_x = -b / (2 * a)
    vertex_y = a * vertex_x**2 + b * vertex_x + c
    ax.scatter([vertex_x], [vertex_y], color="#F44336", s=80, zorder=5)
    ax.text(vertex_x + 0.3, vertex_y + 0.3, f"Tepe ({vertex_x:.1f}, {vertex_y:.1f})", fontsize=10)
    
    ax.set_xlim(-6, 6)
    ax.set_ylim(-6, 12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")


def draw_exponential_function(ax, items: dict, seed=42):
    """Ko'rsatkichli funksiya: y = a^x"""
    a = _parse_numeric(items.get("a", "2"), 2.0)
    
    x = np.linspace(-3, 3, 100)
    y = a ** x
    
    ax.plot(x, y, color="#00897B", linewidth=2.5, label=f"y = {a}ˣ")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.scatter([0], [1], color="#00897B", s=50, zorder=5)
    ax.text(0.2, 1 + 0.3, f"(0, 1)", fontsize=10)
    
    ax.set_xlim(-4, 4)
    ax.set_ylim(-2, 10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")


def draw_logarithmic_function(ax, items: dict, seed=42):
    """Logarifmik funksiya: y = log_a(x)"""
    a = _parse_numeric(items.get("a", "2"), 2.0)
    
    x = np.linspace(0.1, 5, 100)
    y = np.log(x) / np.log(a)
    
    ax.plot(x, y, color="#D84315", linewidth=2.5, label=f"y = log_{a}(x)")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.scatter([1], [0], color="#D84315", s=50, zorder=5)
    ax.text(1.2, 0.3, f"(1, 0)", fontsize=10)
    
    ax.set_xlim(-1, 6)
    ax.set_ylim(-4, 4)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")


# ═════════════════════════════════════════════════════════════════════════════
# TRIGONOMETRIYA
# ═════════════════════════════════════════════════════════════════════════════


def draw_trig_unit_circle(ax, items: dict, seed=42):
    """Birlik aylana - trigonometrik nisbatlar"""
    r = 2
    
    circle = patches.Circle((0, 0), r, facecolor="#E3F2FD", edgecolor="#1565C0", linewidth=2)
    ax.add_patch(circle)
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    angle_deg = _parse_numeric(items.get("angle", "30"), 30.0)
    angle_rad = np.radians(angle_deg)
    
    x = r * np.cos(angle_rad)
    y = r * np.sin(angle_rad)
    
    ax.plot([0, x], [0, y], color="#E53935", linewidth=2)
    ax.plot([x, x], [0, y], color="#43A047", linewidth=1.5, linestyle="--")
    ax.plot([0, x], [y, y], color="#1E88E5", linewidth=1.5, linestyle="--")
    
    ax.scatter([x], [y], color="#E53935", s=80, zorder=5)
    ax.text(x + 0.1, y + 0.1, f"({x:.2f}, {y:.2f})", fontsize=10)
    
    sin_val = np.sin(angle_rad)
    cos_val = np.cos(angle_rad)
    tan_val = np.tan(angle_rad) if abs(angle_rad % np.pi) != np.pi/2 else float('inf')
    
    ax.text(3, 2, f"sin({angle_deg}°) = {sin_val:.3f}", fontsize=11, 
           bbox=dict(boxstyle="round", fc="#FFEBEE", ec="#E53935"))
    ax.text(3, 1, f"cos({angle_deg}°) = {cos_val:.3f}", fontsize=11,
           bbox=dict(boxstyle="round", fc="#E3F2FD", ec="#1E88E5"))
    if tan_val != float('inf'):
        ax.text(3, 0, f"tan({angle_deg}°) = {tan_val:.3f}", fontsize=11,
               bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#43A047"))
    
    arc = patches.Arc((0, 0), r*0.8, r*0.8, angle=0, theta1=0, theta2=angle_deg,
                      color="#E53935", linewidth=2)
    ax.add_patch(arc)
    ax.text(0.3, 0.3, f"{angle_deg}°", fontsize=10, color="#E53935")
    
    ax.set_xlim(-3, 5)
    ax.set_ylim(-3, 3)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)


def draw_trig_identities(ax, items: dict, seed=42):
    """Trigonometrik ayniyatlar"""
    identities = [
        "sin²α + cos²α = 1",
        "tanα = sinα / cosα",
        "1 + tan²α = sec²α",
        "1 + cot²α = csc²α",
        "sin(α + β) = sinα·cosβ + cosα·sinβ",
        "cos(α + β) = cosα·cosβ - sinα·sinβ"
    ]
    
    ax.axis("off")
    
    ax.text(0.5, 0.95, "Trigonometrik ayniyatlar", fontsize=16, fontweight="bold",
           transform=ax.transAxes, ha="center", color="#1565C0")
    
    y_pos = 0.75
    for identity in identities:
        ax.text(0.5, y_pos, identity, fontsize=13, transform=ax.transAxes, ha="center",
               bbox=dict(boxstyle="round,pad=0.3", fc="#F5F5F5", ec="#9E9E9E"))
        y_pos -= 0.12


def draw_sin_cos_graph(ax, items: dict, seed=42):
    """Sinus va kosinus funksiyalari grafigi"""
    x = np.linspace(-2*np.pi, 2*np.pi, 200)
    
    ax.plot(x, np.sin(x), color="#E53935", linewidth=2.5, label="sin(x)")
    ax.plot(x, np.cos(x), color="#1E88E5", linewidth=2.5, label="cos(x)")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.set_xticks([-2*np.pi, -np.pi, 0, np.pi, 2*np.pi])
    ax.set_xticklabels(["-2π", "-π", "0", "π", "2π"])
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    
    ax.set_xlim(-2*np.pi - 0.5, 2*np.pi + 0.5)
    ax.set_ylim(-1.5, 1.5)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    
    ax.set_title("Trigonometrik funksiyalar", fontsize=14, fontweight="bold")


# ═════════════════════════════════════════════════════════════════════════════
# SONLAR VA QATORLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_number_line(ax, items: dict, seed=42):
    """Son o'qi"""
    start = _parse_numeric(items.get("start", "0"), 0.0)
    end = _parse_numeric(items.get("end", "10"), 10.0)
    
    ax.annotate("", xy=(end + 1, 0), xytext=(start - 1, 0),
               arrowprops=dict(arrowstyle="->", color="black", lw=1.5))
    
    for i in range(int(start), int(end) + 1):
        ax.plot([i, i], [-0.1, 0.1], color="black", linewidth=1.5)
        ax.text(i, -0.3, str(i), ha="center", fontsize=11)
    
    ax.set_xlim(start - 1, end + 2)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    ax.set_aspect("equal")


def draw_fraction_circle(ax, items: dict, seed=42):
    """Kasr - doira ko'rinishida"""
    num = _parse_numeric(items.get("numerator", "3"), 3.0)
    denom = _parse_numeric(items.get("denominator", "4"), 4.0)
    
    r = 1.5
    
    circle = patches.Circle((0, 0), r, facecolor="white", edgecolor="#1565C0", linewidth=2)
    ax.add_patch(circle)
    
    wedge_angle = 360 * num / denom
    
    if num / denom <= 0.5:
        wedge = patches.Wedge((0, 0), r, 90, 90 + wedge_angle, facecolor="#E3F2FD", edgecolor="#1565C0", linewidth=2)
    else:
        wedge1 = patches.Wedge((0, 0), r, 90, 270, facecolor="#E3F2FD", edgecolor="#1565C0", linewidth=2)
        wedge2 = patches.Wedge((0, 0), r, 270, 90 + wedge_angle, facecolor="#BBDEFB", edgecolor="#1565C0", linewidth=2)
        ax.add_patch(wedge1)
        wedge = wedge2
    
    ax.add_patch(wedge)
    
    ax.text(0, 0, f"{int(num)}\n────\n{int(denom)}", fontsize=14, ha="center", va="center", fontweight="bold")
    
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-2.5, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_arithmetic_sequence(ax, items: dict, seed=42):
    """Arifmetik progressiya"""
    a1 = _parse_numeric(items.get("a1", "2"), 2.0)
    d = _parse_numeric(items.get("d", "3"), 3.0)
    n = int(_parse_numeric(items.get("n", "6"), 6.0))
    
    terms = [a1 + i * d for i in range(n)]
    
    x_pos = 0
    for i, term in enumerate(terms):
        ax.bar(x_pos, term, width=0.6, color="#3F51B5", alpha=0.8)
        ax.text(x_pos, term + 0.3, f"a{i+1}={term}", ha="center", fontsize=9)
        x_pos += 1
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    
    sn = n * (2 * a1 + (n - 1) * d) / 2
    ax.text(n/2 - 0.5, -1, f"Sₙ = n/2 × (2a₁ + (n-1)d) = {sn:.0f}", fontsize=11,
           bbox=dict(boxstyle="round", fc="#FFF3E0", ec="#E65100"))
    
    ax.set_xticks(range(n))
    ax.set_xticklabels([f"a{i+1}" for i in range(n)])
    ax.set_ylabel("Qiymat")
    ax.grid(True, alpha=0.3, axis="y")


def draw_geometric_sequence(ax, items: dict, seed=42):
    """Geometrik progressiya"""
    a1 = _parse_numeric(items.get("a1", "2"), 2.0)
    q = _parse_numeric(items.get("q", "2"), 2.0)
    n = int(_parse_numeric(items.get("n", "5"), 5.0))
    
    terms = [a1 * (q ** i) for i in range(n)]
    
    x_pos = 0
    for i, term in enumerate(terms):
        ax.bar(x_pos, term, width=0.6, color="#00897B", alpha=0.8)
        ax.text(x_pos, term + 0.5, f"a{i+1}={term:.0f}", ha="center", fontsize=9)
        x_pos += 1
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    
    if abs(q) != 1:
        sn = a1 * (q ** n - 1) / (q - 1)
        ax.text(n/2 - 0.5, -1.5, f"Sₙ = a₁(qⁿ-1)/(q-1) = {sn:.0f}", fontsize=11,
               bbox=dict(boxstyle="round", fc="#E8F5E9", ec="#2E7D32"))
    
    ax.set_xticks(range(n))
    ax.set_xticklabels([f"a{i+1}" for i in range(n)])
    ax.set_ylabel("Qiymat")
    ax.grid(True, alpha=0.3, axis="y")


# ═════════════════════════════════════════════════════════════════════════════
# TEZLIK VA BIRLIKLAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_speed_diagram(ax, items: dict, seed=42):
    """Tezlik masofasi vaqt diagrammasi"""
    v = _parse_numeric(items.get("v", "60"), 60.0)
    t = _parse_numeric(items.get("t", "2"), 2.0)
    
    t_arr = np.linspace(0, t, 50)
    s_arr = v * t_arr
    
    ax.plot(t_arr, s_arr, color="#E53935", linewidth=3, label=f"v = {v} km/soat")
    
    ax.fill_between(t_arr, s_arr, alpha=0.2, color="#E53935")
    
    ax.scatter([t], [v * t], color="#E53935", s=100, zorder=5)
    ax.text(t + 0.1, v * t, f"({t} soat, {v*t:.0f} km)", fontsize=11)
    
    s = v * t
    ax.text(t/2, s/2, f"Masofa = {s:.0f} km", fontsize=12, rotation=np.degrees(np.arctan(v/10)),
           bbox=dict(boxstyle="round", fc="#FFEBEE", ec="#E53935"))
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.set_xlabel("Vaqt (soat)")
    ax.set_ylabel("Masofa (km)")
    ax.set_xlim(-0.5, t + 1)
    ax.set_ylim(-10, s + 10)
    ax.grid(True, alpha=0.3)
    ax.legend()


# ═════════════════════════════════════════════════════════════════════════════
# EHTIMOLLIK VA STATISTIKA
# ═════════════════════════════════════════════════════════════════════════════


def draw_probability_tree(ax, items: dict, seed=42):
    """Ehtimollik daraxti"""
    ax.axis("off")
    
    ax.text(0.5, 0.95, "Ehtimollik daraxti", fontsize=16, fontweight="bold",
           transform=ax.transAxes, ha="center", color="#1565C0")
    
    ax.text(0.2, 0.7, "A", fontsize=14, fontweight="bold", transform=ax.transAxes)
    ax.plot([0.25, 0.4], [0.7, 0.5], "b-", lw=2, transform=ax.transAxes)
    ax.text(0.42, 0.5, "P(A) = 0.3", fontsize=10, transform=ax.transAxes)
    
    ax.plot([0.25, 0.4], [0.7, 0.9], "b-", lw=2, transform=ax.transAxes)
    ax.text(0.42, 0.9, "P(A') = 0.7", fontsize=10, transform=ax.transAxes)
    
    ax.text(0.6, 0.35, "B", fontsize=14, fontweight="bold", transform=ax.transAxes)
    ax.plot([0.45, 0.58], [0.5, 0.35], "g-", lw=2, transform=ax.transAxes)
    ax.text(0.6, 0.22, "P(B|A)", fontsize=10, transform=ax.transAxes)
    
    ax.text(0.6, 0.75, "B", fontsize=14, fontweight="bold", transform=ax.transAxes)
    ax.plot([0.45, 0.58], [0.9, 0.75], "g-", lw=2, transform=ax.transAxes)
    ax.text(0.6, 0.62, "P(B|A')", fontsize=10, transform=ax.transAxes)


def draw_bar_chart(ax, items: dict, seed=42):
    """Ustunli diagramma"""
    labels = ["1-sinf", "2-sinf", "3-sinf", "4-sinf", "5-sinf"]
    values = [85, 92, 78, 95, 88]
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    
    bars = ax.bar(labels, values, color=colors, edgecolor="black", linewidth=1.5)
    
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
               str(val), ha="center", fontsize=11, fontweight="bold")
    
    ax.set_ylabel("Ball")
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_title("Sinf bo'yicha o'rtacha ballar", fontsize=14, fontweight="bold")


def draw_pie_chart(ax, items: dict, seed=42):
    """Doiraviy diagramma"""
    labels = ["Algebra", "Geometriya", "Mantiq", "Statistika"]
    sizes = [35, 25, 25, 15]
    colors_pie = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444"]
    explode = (0.05, 0, 0, 0)
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
           autopct="%1.0f%%", shadow=True, startangle=90,
           wedgeprops={"edgecolor": "black", "linewidth": 1.5})
    
    ax.set_title("Fanlar bo'yicha taqsimot", fontsize=14, fontweight="bold")


# ═════════════════════════════════════════════════════════════════════════════
# KESIMLAR VA PROYEKSIYALAR
# ═════════════════════════════════════════════════════════════════════════════


def draw_cube_section(ax, items: dict, seed=42):
    """Kub kesimi"""
    s = 2
    
    vertices = {
        "A": (0, 0, 0), "B": (s, 0, 0), "C": (s, s, 0), "D": (0, s, 0),
        "E": (0, 0, s), "F": (s, 0, s), "G": (s, s, s), "H": (0, s, s)
    }
    
    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"),
             ("E", "F"), ("F", "G"), ("G", "H"), ("H", "E"),
             ("A", "E"), ("B", "F"), ("C", "G"), ("D", "H")]
    
    for e in edges:
        p1, p2 = vertices[e[0]], vertices[e[1]]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], "b-", lw=2)
    
    section_pts = [
        [s*0.5, 0, 0], [s, s*0.5, 0], [s*0.5, s, 0],
        [0, s*0.5, s], [s*0.5, 0, s]
    ]
    
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    
    verts = [[section_pts[0], section_pts[1], section_pts[2], section_pts[3]]]
    ax.add_collection3d(Poly3DCollection(verts, alpha=0.3, facecolor="red", edgecolor="red", lw=2))
    
    for pt in section_pts:
        ax.scatter(*pt, color="red", s=50)
    
    ax.text(s/2, -0.5, s/2, f"Kub kesimi", fontsize=10)


def draw_coordinate_system(ax, items: dict, seed=42):
    """Koordinata sistemasida nuqta"""
    x0 = _parse_numeric(items.get("x", "3"), 3.0)
    y0 = _parse_numeric(items.get("y", "2"), 2.0)
    
    ax.axhline(y=0, color="black", linewidth=1)
    ax.axvline(x=0, color="black", linewidth=1)
    
    ax.scatter([x0], [y0], color="#E53935", s=100, zorder=5)
    
    ax.plot([0, x0], [y0, y0], color="#1E88E5", linewidth=1.5, linestyle="--")
    ax.plot([x0, x0], [0, y0], color="#43A047", linewidth=1.5, linestyle="--")
    
    ax.text(x0, y0 + 0.3, f"M({x0}, {y0})", fontsize=12, fontweight="bold", color="#E53935")
    
    ax.text(x0/2, y0 - 0.3, f"x = {x0}", fontsize=10, color="#1E88E5", ha="center")
    ax.text(x0 + 0.2, y0/2, f"y = {y0}", fontsize=10, color="#43A047", rotation=90, va="center")
    
    ax.set_xlim(-1, max(x0 + 2, 6))
    ax.set_ylim(-1, max(y0 + 2, 6))
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")


# ═════════════════════════════════════════════════════════════════════════════
# INTEGRAL VA HOSILA
# ═════════════════════════════════════════════════════════════════════════════


def draw_derivative_graph(ax, items: dict, seed=42):
    """Hosila grafigi"""
    x = np.linspace(-3, 3, 100)
    
    f = x**2
    f_prime = 2 * x
    
    ax.plot(x, f, "b-", linewidth=2, label="f(x) = x²")
    ax.plot(x, f_prime, "r-", linewidth=2, label="f'(x) = 2x")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    ax.scatter([0], [0], color="#E53935", s=80, zorder=5)
    ax.text(0.2, 0.5, "f'(0) = 0", fontsize=11)
    
    ax.set_xlim(-4, 4)
    ax.set_ylim(-2, 10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_title("Hosila", fontsize=14, fontweight="bold")


def draw_integral_graph(ax, items: dict, seed=42):
    """Integral grafigi"""
    x = np.linspace(-2, 2, 100)
    y = x**2
    
    ax.plot(x, y, "b-", linewidth=2, label="f(x) = x²")
    ax.fill_between(x, y, alpha=0.3, color="blue")
    
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=0, color="black", linewidth=0.8)
    
    integral_val = 16/3
    ax.text(0, 2, f"∫x²dx = {integral_val:.2f}", fontsize=12,
           bbox=dict(boxstyle="round", fc="#FFF3E0", ec="#E65100"))
    
    ax.set_xlim(-3, 3)
    ax.set_ylim(-1, 5)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_title("Integral", fontsize=14, fontweight="bold")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN DRAWING FUNCTION
# ═════════════════════════════════════════════════════════════════════════════


def draw_geometry(shape: str, items: dict, figsize=(8, 6), seed=42) -> bytes:
    """Barcha shakllarni chizish uchun asosiy funksiya"""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    
    shape_lower = shape.lower()
    
    if shape_lower in ("3d_cube", "kub"):
        draw_3d_cube(ax, items, seed)
    elif shape_lower in ("3d_prism", "prizma"):
        draw_3d_prism(ax, items, seed)
    elif shape_lower in ("3d_pyramid", "piramida"):
        draw_3d_pyramid(ax, items, seed)
    elif shape_lower in ("3d_cylinder", "silindr"):
        draw_3d_cylinder(ax, items, seed)
    elif shape_lower in ("3d_cone", "konus"):
        draw_3d_cone(ax, items, seed)
    elif shape_lower in ("3d_sphere", "shar"):
        draw_3d_sphere(ax, items, seed)
    elif shape_lower in ("linear", "chiziqli"):
        draw_linear_function(ax, items, seed)
    elif shape_lower in ("quadratic", "kvadrat"):
        draw_quadratic_function(ax, items, seed)
    elif shape_lower in ("exponential", "korsatkichli"):
        draw_exponential_function(ax, items, seed)
    elif shape_lower in ("logarithmic", "logarifmik"):
        draw_logarithmic_function(ax, items, seed)
    elif shape_lower == "trig_unit":
        draw_trig_unit_circle(ax, items, seed)
    elif shape_lower in ("trig_identity", "trig_identities"):
        draw_trig_identities(ax, items, seed)
    elif shape_lower in ("sin_cos_graph", "sin_cos"):
        draw_sin_cos_graph(ax, items, seed)
    elif shape_lower == "number_line":
        draw_number_line(ax, items, seed)
    elif shape_lower in ("fraction", "kasr"):
        draw_fraction_circle(ax, items, seed)
    elif shape_lower in ("arithmetic", "arifmetik"):
        draw_arithmetic_sequence(ax, items, seed)
    elif shape_lower in ("geometric", "geometrik"):
        draw_geometric_sequence(ax, items, seed)
    elif shape_lower in ("speed", "tezlik"):
        draw_speed_diagram(ax, items, seed)
    elif shape_lower in ("probability", "ehtimollik"):
        draw_probability_tree(ax, items, seed)
    elif shape_lower == "bar_chart":
        draw_bar_chart(ax, items, seed)
    elif shape_lower == "pie_chart":
        draw_pie_chart(ax, items, seed)
    elif shape_lower in ("section", "kesim"):
        draw_cube_section(ax, items, seed)
    elif shape_lower in ("coordinate", "koordinata"):
        draw_coordinate_system(ax, items, seed)
    elif shape_lower in ("derivative", "hosila"):
        draw_derivative_graph(ax, items, seed)
    elif shape_lower in ("integral",):
        draw_integral_graph(ax, items, seed)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    img_bytes = buf.getvalue()
    plt.close()
    
    return img_bytes
