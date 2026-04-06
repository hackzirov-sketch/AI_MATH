"""
services/tikz_templates.py — TIKZ TEMPLATE PATTERNS

Tez-tez ishlatiladigan diagrammalar uchun ready-to-use TikZ kod.
RenderSpec → TikZ template shablonlari.
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Optional
from services.tikz_styles import latex_escape


class TikzTemplateLibrary:
    """
    TikZ template patterns for common math diagrams.
    Each static method returns a complete tikzpicture string.
    """

    @staticmethod
    def triangle(vertices: List[Tuple[float, float]],
                 labels: List[str] = None,
                 side_labels: List[str] = None,
                 angle_labels: List[str] = None,
                 show_right_angle: int = -1) -> str:
        """Uchburchak TikZ template"""
        if labels is None:
            labels = ["A", "B", "C"]
        if len(vertices) != 3:
            return "% Invalid triangle"

        v1, v2, v3 = vertices
        lines = [
            r"\begin{tikzpicture}",
            f"  \\draw ({v1[0]:.2f}, {v1[1]:.2f}) -- ({v2[0]:.2f}, {v2[1]:.2f}) -- ({v3[0]:.2f}, {v3[1]:.2f}) -- cycle;"
        ]

        cx = sum(v[0] for v in vertices) / 3
        cy = sum(v[1] for v in vertices) / 3

        for i, (v, lbl) in enumerate(zip(vertices, labels)):
            dx, dy = v[0] - cx, v[1] - cy
            d = max((dx**2 + dy**2)**0.5, 0.01)
            ox, oy = dx / d * 0.35, dy / d * 0.35
            lines.append(f"  \\node[font=\\bfseries] at ({v[0]+ox:.2f}, {v[1]+oy:.2f}) {{{lbl}}};")

        if side_labels:
            pairs = [(v1, v2), (v2, v3), (v1, v3)]
            for i, lbl in enumerate(side_labels):
                if i < len(pairs) and lbl:
                    pa, pb = pairs[i]
                    mx, my = (pa[0]+pb[0])/2, (pa[1]+pb[1])/2
                    dx, dy = pb[0]-pa[0], pb[1]-pa[1]
                    d = max((dx**2 + dy**2)**0.5, 0.01)
                    nx, ny = -dy/d * 0.25, dx/d * 0.25
                    lines.append(f"  \\node[font=\\small] at ({mx+nx:.2f}, {my+ny:.2f}) {{{lbl}}};")

        if angle_labels:
            for i, lbl in enumerate(angle_labels):
                if lbl and i < 3:
                    v = vertices[i]
                    p1 = vertices[(i+1) % 3]
                    p2 = vertices[(i+2) % 3]
                    import math
                    a1 = math.degrees(math.atan2(p1[1]-v[1], p1[0]-v[0]))
                    a2 = math.degrees(math.atan2(p2[1]-v[1], p2[0]-v[0]))
                    mid = (a1 + a2) / 2
                    if show_right_angle == i:
                        lines.append(f"  % Right angle at {labels[i]}")
                    else:
                        lx = v[0] + 0.35 * math.cos(math.radians(mid))
                        ly = v[1] + 0.35 * math.sin(math.radians(mid))
                        lines.append(f"  \\node[font=\\small\\itshape] at ({lx:.2f}, {ly:.2f}) {{{lbl}}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def rectangle(width: float, height: float,
                  labels: List[str] = None,
                  show_diagonal: bool = False,
                  side_labels: List[str] = None) -> str:
        """To'g'ri to'rtburchak TikZ template"""
        if labels is None:
            labels = ["A", "B", "C", "D"]
        corners = [(0, 0), (width, 0), (width, height), (0, height)]
        offsets = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]

        lines = [
            r"\begin{tikzpicture}",
            f"  \\draw (0, 0) rectangle ({width:.2f}, {height:.2f});"
        ]

        for (x, y), (ox, oy), lbl in zip(corners, offsets, labels):
            lines.append(f"  \\node[font=\\bfseries] at ({x+ox:.2f}, {y+oy:.2f}) {{{lbl}}};")

        if show_diagonal:
            lines.append(f"  \\draw[dashed] (0, 0) -- ({width:.2f}, {height:.2f});")

        if side_labels:
            midpoints = [(width/2, -0.25), (width+0.25, height/2), (width/2, height+0.25), (-0.25, height/2)]
            for lbl, (mx, my) in zip(side_labels[:4], midpoints):
                if lbl:
                    lines.append(f"  \\node[font=\\small] at ({mx:.2f}, {my:.2f}) {{{lbl}}};")

        # Right angle marks at corners
        sq = 0.15
        for cx, cy in corners:
            sx = sq if cx == 0 else -sq
            sy = sq if cy == 0 else -sq
            lines.append(f"  \\draw ({cx+sx:.2f}, {cy:.2f}) -- ({cx+sx:.2f}, {cy+sy:.2f}) -- ({cx:.2f}, {cy+sy:.2f});")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def circle(radius: float, center_label: str = "O",
               show_radius: bool = True,
               radius_label: str = "r",
               show_diameter: bool = False) -> str:
        """Aylana TikZ template"""
        lines = [
            r"\begin{tikzpicture}",
            f"  \\draw (0, 0) circle ({radius:.2f});",
            f"  \\fill (0, 0) circle (1.5pt);",
            f"  \\node[font=\\bfseries, below left] at (-0.1, -0.1) {{{center_label}}};"
        ]

        if show_radius:
            import math
            angle = -25
            ex = radius * math.cos(math.radians(angle))
            ey = radius * math.sin(math.radians(angle))
            lines.append(f"  \\draw[dashed] (0, 0) -- ({ex:.2f}, {ey:.2f});")
            lines.append(f"  \\node[font=\\small, below] at ({ex/2:.2f}, {ey/2-0.1:.2f}) {{$\\mathrm{{{radius_label}}}$}};")

        if show_diameter:
            lines.append(f"  \\draw[dashed] ({-radius*0.95:.2f}, 0) -- ({radius*0.95:.2f}, 0);")
            lines.append(f"  \\node[font=\\small, below] at (0, -0.15) {{$d$}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def flow_diagram(nodes: List[Tuple[str, str]],
                     node_width: float = 1.8,
                     spacing: float = 2.2) -> str:
        """Oqim diagramma TikZ template"""
        lines = [r"\begin{tikzpicture}[node distance={spacing:.1f}cm]".replace("{spacing:.1f}", f"{spacing:.1f}")]

        for i, (content, _) in enumerate(nodes):
            pos = f"right={spacing:.1f}cm of n{i-1}" if i > 0 else ""
            comma = ", " if pos else ""
            lines.append(f"  \\node[draw, rounded corners, minimum width={node_width:.1f}cm, minimum height=0.8cm{comma}{pos}] (n{i}) {{{latex_escape(content)}}};")

        for i in range(len(nodes) - 1):
            lines.append(f"  \\draw[->, >=stealth] (n{i}) -- (n{i+1});")

        for i, (_, op) in enumerate(nodes):
            if op and i < len(nodes) - 1:
                lines.append(f"  \\node[font=\\small, above] at ($(n{i})!.5!(n{i+1})$) {{{latex_escape(op)}}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def chain_circles(values: List[str],
                      radius: float = 0.5,
                      spacing: float = 1.8) -> str:
        """Zanjir doiralar TikZ template"""
        lines = [r"\begin{tikzpicture}"]

        for i, val in enumerate(values):
            x = i * spacing
            lines.append(f"  \\draw ({x:.2f}, 0) circle ({radius:.2f}cm) node {{{latex_escape(val)}}};")
            if i > 0:
                prev_x = (i - 1) * spacing
                lines.append(f"  \\draw[->, >=stealth] ({prev_x+radius:.2f}, 0) -- ({x-radius:.2f}, 0);")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def grid(rows: int, cols: int,
             cell_size: float = 1.0,
             contents: List[List[str]] = None,
             unknown_cells: List[Tuple[int, int]] = None) -> str:
        """Jadval TikZ template"""
        lines = [r"\begin{tikzpicture}"]

        if unknown_cells is None:
            unknown_cells = []

        for r in range(rows):
            for c in range(cols):
                x = c * cell_size
                y = -r * cell_size
                content = "?"
                if contents and r < len(contents) and c < len(contents[r]):
                    content = str(contents[r][c])

                is_unknown = (r, c) in unknown_cells
                style = ", fill=yellow!20, draw=orange!80!black" if is_unknown else ""
                lines.append(f"  \\node[draw, minimum size={cell_size:.1f}cm{style}] at ({x:.2f}, {y:.2f}) {{{latex_escape(content)}}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def vertical_arithmetic(a: int, b: int, op: str = "+",
                            result: Optional[int] = None,
                            show_unknown: bool = False) -> str:
        """Vertikal arifmetika TikZ template"""
        if result is None:
            result = a + b if op == "+" else a - b if op == "-" else a * b

        lines = [r"\begin{tikzpicture}"]

        lines.append(f"  \\node[font=\\large\\ttfamily, anchor=east] at (2, 1.2) {{{a}}};")
        lines.append(f"  \\node[font=\\large\\ttfamily, anchor=east] at (1.5, 0.6) {{{op}}};")
        lines.append(f"  \\node[font=\\large\\ttfamily, anchor=east] at (2, 0.6) {{{b}}};")
        lines.append(f"  \\draw (0.8, 0.3) -- (2.2, 0.3);")

        if show_unknown:
            lines.append(f"  \\node[font=\\large\\bfseries, red!70!black, anchor=east] at (2, -0.3) {{$?$}};")
        else:
            lines.append(f"  \\node[font=\\large\\ttfamily\\bfseries, anchor=east] at (2, -0.3) {{{result}}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)

    @staticmethod
    def number_line(start: int, end: int,
                    marks: List[Tuple[float, str]] = None,
                    unknown_pos: Optional[float] = None) -> str:
        """Son o'qi TikZ template"""
        lines = [r"\begin{tikzpicture}"]

        length = end - start
        lines.append(f"  \\draw[->, >=stealth] ({start-0.5:.1f}, 0) -- ({end+0.5:.1f}, 0);")

        for i in range(start, end + 1):
            lines.append(f"  \\draw ({i:.1f}, -0.1) -- ({i:.1f}, 0.1);")
            lines.append(f"  \\node[below, font=\\small] at ({i:.1f}, -0.1) {{{i}}};")

        if marks:
            for pos, label in marks:
                lines.append(f"  \\fill[blue] ({pos:.2f}, 0) circle (3pt);")
                lines.append(f"  \\node[above, font=\\small\\bfseries, blue] at ({pos:.2f}, 0.1) {{{label}}};")

        if unknown_pos is not None:
            lines.append(f"  \\fill[red!70!black] ({unknown_pos:.2f}, 0) circle (4pt);")
            lines.append(f"  \\node[above, font=\\large\\bfseries, red!70!black] at ({unknown_pos:.2f}, 0.15) {{$x$}};")

        lines.append(r"\end{tikzpicture}")
        return "\n".join(lines)


tikz_template_library = TikzTemplateLibrary()
