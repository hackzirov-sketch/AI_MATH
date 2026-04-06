"""
services/tikz_styles.py — ACADEMIC TIKZ STYLE DEFINITIONS

Minimal, academic, print-friendly TikZ style definitions.
Default: white background, black lines, black text.
"""

from __future__ import annotations
from typing import Dict


TIKZ_DEFAULT_STYLE = {
    "line_width": "0.8pt",
    "line_color": "black",
    "fill_color": "none",
    "text_color": "black",
    "font_size": "\\small",
    "point_radius": "1.5pt",
    "tick_length": "3pt",
    "arrow_style": "->, >=stealth",
    "label_offset": "4pt",
}


TIKZ_STYLESHEET = r"""
% ─── Academic Math TikZ Styles ─────────────────────────────
% Usage: \input{tikz_styles.tex} or copy below to preamble

\usepackage{tikz}
\usetikzlibrary{calc, arrows.meta, positioning, decorations.markings}

% Core geometry styles
\tikzset{
    % ── Basic elements ──
    geo point/.style={
        circle,
        fill=black,
        inner sep=1.5pt,
    },
    geo segment/.style={
        line width=0.8pt,
        color=black,
    },
    geo dashed/.style={
        dashed,
        line width=0.6pt,
        color=black!60,
    },
    geo ray/.style={
        -{Stealth[length=3mm]},
        line width=0.8pt,
        color=black,
    },
    geo line/.style{
        line width=0.6pt,
        dashed,
        color=black!50,
    },
    % ── Shapes ──
    geo triangle/.style={
        line width=0.8pt,
        color=black,
        fill=none,
    },
    geo rectangle/.style={
        line width=0.8pt,
        color=black,
        fill=none,
    },
    geo circle/.style={
        line width=0.8pt,
        color=black,
        fill=none,
    },
    % ── Labels ──
    vertex label/.style={
        font=\bfseries\small,
        color=black,
    },
    side label/.style{
        font=\small,
        color=black,
        midway,
    },
    angle label/.style={
        font=\small\itshape,
        color=black,
    },
    measurement/.style{
        font=\small,
        color=black!70,
    },
    % ── Angle markers ──
    angle arc/.style{
        line width=0.6pt,
        color=black,
    },
    right angle/.style{
        line width=0.6pt,
        color=black,
    },
    % ── Tick marks ──
    tick mark/.style{
        line width=0.6pt,
        color=black,
        shorten >=1pt,
        shorten <=1pt,
    },
    parallel mark/.style{
        line width=0.5pt,
        color=black,
    },
    % ── Unknown / question ──
    unknown marker/.style{
        font=\large\bfseries,
        color=red!70!black,
    },
    question box/.style{
        draw=black,
        line width=0.8pt,
        fill=yellow!10,
        minimum width=1cm,
        minimum height=0.6cm,
        rounded corners=2pt,
    },
    % ── Flow / Puzzle ──
    flow node/.style{
        draw=black,
        line width=0.8pt,
        fill=none,
        minimum width=1.5cm,
        minimum height=0.8cm,
        rounded corners=3pt,
        font=\small,
    },
    flow arrow/.style{
        -{Stealth[length=2.5mm]},
        line width=0.8pt,
        color=black,
    },
    chain circle/.style{
        draw=black,
        line width=0.8pt,
        fill=none,
        circle,
        minimum size=1cm,
        font=\small,
    },
    grid cell/.style{
        draw=black,
        line width=0.8pt,
        fill=none,
        minimum size=1cm,
        font=\small,
    },
    % ── Answer highlight (optional) ──
    answer highlight/.style{
        draw=black,
        line width=1pt,
        fill=yellow!15,
        rounded corners=2pt,
    },
}
"""


def get_style_preset(preset_name: str) -> Dict[str, str]:
    """Style preset olish"""
    presets = {
        "academic": TIKZ_DEFAULT_STYLE.copy(),
        "print_friendly": {
            **TIKZ_DEFAULT_STYLE,
            "line_width": "0.6pt",
        },
        "high_contrast": {
            **TIKZ_DEFAULT_STYLE,
            "line_width": "1.2pt",
        },
        "minimal": {
            **TIKZ_DEFAULT_STYLE,
            "line_width": "0.4pt",
        },
    }
    return presets.get(preset_name, TIKZ_DEFAULT_STYLE.copy())


def get_tikz_preamble() -> str:
    """Full TikZ preamble for standalone documents"""
    return r"""\documentclass[tikz, border=5mm]{standalone}
\usepackage{tikz}
\usetikzlibrary{calc, arrows.meta, positioning, decorations.markings}
\usepackage[utf8]{inputenc}
\usepackage[T2A]{fontenc}
\usepackage[russian, english]{babel}
"""


def latex_escape(text: str) -> str:
    """LaTeX-safe text escaping"""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
