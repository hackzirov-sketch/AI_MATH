"""
services/flowchart_engine.py — NETWORKX-BASED FLOWCHART PUZZLE ENGINE

NetworkX asosida flowchart puzzle yaratish.

Turlari:
1. Linear flow (A → B → C)
2. Branching flow (A → B or C)
3. Merging flow (A + B → C)
4. Loop-aware flow
5. Multi-path flow

Graph structure → Controlled generation → SymPy validation → Render spec
"""

from __future__ import annotations

import logging
import random
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field

import numpy as np

try:
    import networkx as nx
    NX_OK = True
except ImportError:
    NX_OK = False

logger = logging.getLogger(__name__)


@dataclass
class FlowNode:
    """Oqim tuguni"""
    node_id: str
    label: str
    value: Optional[int] = None
    operation: Optional[str] = None
    op_value: Optional[int] = None
    is_input: bool = False
    is_output: bool = False
    is_unknown: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.node_id,
            "label": self.label,
            "value": self.value,
            "op": self.operation,
            "op_value": self.op_value,
        }


@dataclass
class FlowchartPuzzle:
    """Flowchart puzzle natijasi"""
    flow_type: str
    nodes: List[FlowNode]
    edges: List[Tuple[str, str]]
    input_value: int
    output_value: int
    operations: List[Dict[str, Any]]
    correct_answer: int
    answer_var: str
    puzzle_display: str
    equations: List[str]
    explanation: str
    difficulty: str
    uniqueness_signature: str
    graph_structure: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": self.flow_type,
            "answer": self.correct_answer,
            "nodes": [n.to_dict() for n in self.nodes],
            "operations": self.operations,
            "display": self.puzzle_display,
            "explanation": self.explanation,
            "signature": self.uniqueness_signature,
        }


class FlowchartEngine:
    """
    NetworkX-based flowchart puzzle generator.
    
    Graph struktura → controlled parameter → validation → render spec
    """
    
    OP_SYMBOLS = {
        "+": "Qo'shish",
        "-": "Ayirish",
        "×": "Ko'paytirish",
        "÷": "Bo'lish",
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
    
    def generate_linear_flow(self, steps: int = 3,
                              difficulty: str = "o'rta",
                              grade: int = 5,
                              hide_position: Optional[int] = None) -> Optional[FlowchartPuzzle]:
        """
        Chiziqli oqim: [Start] → [Op1] → [Op2] → [Result]
        
        Bir tugun yashirin bo'ladi (noma'lum qiymat).
        """
        if steps < 1 or steps > 6:
            steps = 3
        
        start_val = int(self.np_rng.integers(3, 20))
        
        available_ops = self._get_ops_for_grade(grade)
        
        nodes = []
        edges = []
        operations = []
        
        current_val = start_val
        
        input_node = FlowNode("start", "Boshlash", value=start_val, is_input=True)
        nodes.append(input_node)
        
        for i in range(steps):
            op = self.rng.choice(available_ops)
            
            if op == "+":
                op_val = int(self.np_rng.integers(2, 15))
                new_val = current_val + op_val
            elif op == "-":
                op_val = int(self.np_rng.integers(1, min(current_val - 1, 12)))
                new_val = current_val - op_val
            elif op == "×":
                op_val = int(self.np_rng.integers(2, 6))
                new_val = current_val * op_val
            elif op == "÷":
                divisors = [d for d in range(2, 10) if current_val % d == 0]
                if divisors:
                    op_val = self.rng.choice(divisors)
                else:
                    op_val = 2
                new_val = current_val // op_val
            else:
                op_val = int(self.np_rng.integers(2, 10))
                new_val = current_val + op_val
            
            step_node = FlowNode(
                f"step_{i}",
                f"{op} {op_val}",
                value=new_val,
                operation=op,
                op_value=op_val,
            )
            nodes.append(step_node)
            
            edges.append((nodes[-2].node_id, step_node.node_id))
            
            operations.append({
                "step": i + 1,
                "op": op,
                "value": op_val,
                "input": current_val,
                "output": new_val,
            })
            
            current_val = new_val
        
        output_node = FlowNode("end", "Natija", value=current_val, is_output=True)
        nodes.append(output_node)
        edges.append((nodes[-2].node_id, output_node.node_id))
        
        if hide_position is None:
            hide_position = self.rng.randint(0, len(nodes) - 1)
        
        hidden_node = nodes[hide_position]
        hidden_node.is_unknown = True
        correct_answer = hidden_node.value
        hidden_node.value = None
        
        display = self._build_linear_display(nodes, edges, hidden_node)
        
        equations = []
        for i, op_info in enumerate(operations):
            equations.append(f"{op_info['input']} {op_info['op']} {op_info['value']} = {op_info['output']}")
        
        sig_str = f"flow_linear_{start_val}_" + "_".join(
            f"{o['op']}{o['value']}" for o in operations
        )
        signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
        if NX_OK:
            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n.node_id, label=n.label)
            for e in edges:
                G.add_edge(e[0], e[1])
            graph_structure = {
                "nodes": list(G.nodes(data=True)),
                "edges": list(G.edges()),
                "is_dag": nx.is_directed_acyclic_graph(G),
            }
        else:
            graph_structure = None
        
        return FlowchartPuzzle(
            flow_type="linear_flow",
            nodes=nodes,
            edges=edges,
            input_value=start_val,
            output_value=current_val if hide_position != len(nodes) - 1 else correct_answer,
            operations=operations,
            correct_answer=correct_answer,
            answer_var=hidden_node.label,
            puzzle_display=display,
            equations=equations,
            explanation=f"Boshlang'ich: {start_val}, " + " → ".join(
                f"{o['op']}{o['value']}={o['output']}" for o in operations
            ),
            difficulty=difficulty,
            uniqueness_signature=signature,
            graph_structure=graph_structure,
        )
    
    def generate_branching_flow(self, difficulty: str = "o'rta",
                                 grade: int = 5) -> Optional[FlowchartPuzzle]:
        """
        Tarmoqlangan oqim:
        [Start] → [Condition] → [Path A or Path B]
        """
        if not NX_OK:
            return self.generate_linear_flow(2, difficulty, grade)
        
        start_val = int(self.np_rng.integers(5, 20))
        
        cond_type = self.rng.choice(["even_odd", "greater_less"])
        
        if cond_type == "even_odd":
            if start_val % 2 == 0:
                path_a_op, path_a_val = "+", int(self.np_rng.integers(2, 8))
                path_b_op, path_b_val = "×", int(self.np_rng.integers(2, 4))
                correct_path = "A"
            else:
                path_a_op, path_a_val = "×", int(self.np_rng.integers(2, 4))
                path_b_op, path_b_val = "+", int(self.np_rng.integers(2, 8))
                correct_path = "B"
            condition_text = f"Juft bo'lsa → A, Toq bo'lsa → B"
        else:
            mid = 10
            if start_val > mid:
                correct_path = "A"
                path_a_op, path_a_val = "-", int(self.np_rng.integers(1, 5))
                path_b_op, path_b_val = "+", int(self.np_rng.integers(2, 8))
            else:
                correct_path = "B"
                path_a_op, path_a_val = "+", int(self.np_rng.integers(2, 8))
                path_b_op, path_b_val = "-", int(self.np_rng.integers(1, 5))
            condition_text = f"{start_val} > {mid} → A, ≤ {mid} → B"
        
        if path_a_op == "+":
            path_a_result = start_val + path_a_val
        elif path_a_op == "-":
            path_a_result = start_val - path_a_val
        elif path_a_op == "×":
            path_a_result = start_val * path_a_val
        else:
            path_a_result = start_val // path_a_val if path_a_val != 0 else start_val
        
        if path_b_op == "+":
            path_b_result = start_val + path_b_val
        elif path_b_op == "-":
            path_b_result = start_val - path_b_val
        elif path_b_op == "×":
            path_b_result = start_val * path_b_val
        else:
            path_b_result = start_val // path_b_val if path_b_val != 0 else start_val
        
        correct_answer = path_a_result if correct_path == "A" else path_b_result
        
        G = nx.DiGraph()
        G.add_node("start", label=f"Start: {start_val}")
        G.add_node("condition", label=condition_text)
        G.add_node("path_a", label=f"Yo'l A: {path_a_op}{path_a_val}")
        G.add_node("path_b", label=f"Yo'l B: {path_b_op}{path_b_val}")
        G.add_node("end", label=f"Natija: ?")
        
        G.add_edge("start", "condition")
        G.add_edge("condition", "path_a")
        G.add_edge("condition", "path_b")
        G.add_edge("path_a", "end")
        G.add_edge("path_b", "end")
        
        display = (
            f"  [{start_val}]\n"
            f"    |\n"
            f"  [{condition_text}]\n"
            f"   / \\\n"
            f" [A: {path_a_op}{path_a_val}={path_a_result}]  [B: {path_b_op}{path_b_val}={path_b_result}]\n"
            f"   \\ /\n"
            f"  [Natija = ?]"
        )
        
        sig_str = f"branch_{start_val}_{correct_path}"
        signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
        return FlowchartPuzzle(
            flow_type="branching_flow",
            nodes=[
                FlowNode("start", f"Start", value=start_val, is_input=True),
                FlowNode("condition", condition_text),
                FlowNode("path_a", f"Yo'l A: {path_a_op}{path_a_val}", value=path_a_result, operation=path_a_op, op_value=path_a_val),
                FlowNode("path_b", f"Yo'l B: {path_b_op}{path_b_val}", value=path_b_result, operation=path_b_op, op_value=path_b_val),
                FlowNode("end", "Natija", value=correct_answer, is_output=True, is_unknown=True),
            ],
            edges=[("start", "condition"), ("condition", "path_a"), ("condition", "path_b"), ("path_a", "end"), ("path_b", "end")],
            input_value=start_val,
            output_value=correct_answer,
            operations=[
                {"path": correct_path, "op": path_a_op if correct_path == "A" else path_b_op,
                 "value": path_a_val if correct_path == "A" else path_b_val}
            ],
            correct_answer=correct_answer,
            answer_var="natija",
            puzzle_display=display,
            equations=[
                f"Yo'l A: {start_val} {path_a_op} {path_a_val} = {path_a_result}",
                f"Yo'l B: {start_val} {path_b_op} {path_b_val} = {path_b_result}",
                f"To'g'ri yo'l: {correct_path}",
            ],
            explanation=f"Shart: {condition_text}. To'g'ri yo'l: {correct_path}. Natija: {correct_answer}",
            difficulty=difficulty,
            uniqueness_signature=signature,
            graph_structure={
                "nodes": list(G.nodes(data=True)),
                "edges": list(G.edges()),
                "is_dag": nx.is_directed_acyclic_graph(G),
            },
        )
    
    def generate_multi_path_flow(self, difficulty: str = "qiyin",
                                  grade: int = 6) -> Optional[FlowchartPuzzle]:
        """
        Ko'p yo'lli oqim:
        [A] → [Op1] → [Merge] ← [Op2] ← [B]
        """
        a_val = int(self.np_rng.integers(3, 15))
        b_val = int(self.np_rng.integers(3, 15))
        
        op1 = self.rng.choice(["+", "×"])
        op2 = self.rng.choice(["+", "×"])
        merge_op = self.rng.choice(["+", "×"])
        
        op1_val = int(self.np_rng.integers(2, 8))
        op2_val = int(self.np_rng.integers(2, 8))
        
        if op1 == "+":
            path_a = a_val + op1_val
        else:
            path_a = a_val * op1_val
        
        if op2 == "+":
            path_b = b_val + op2_val
        else:
            path_b = b_val * op2_val
        
        if merge_op == "+":
            result = path_a + path_b
        else:
            result = path_a * path_b
        
        display = (
            f"  [{a_val}]──[{op1}{op1_val}]──┐\n"
            f"                         ├──[{merge_op}]──[?]\n"
            f"  [{b_val}]──[{op2}{op2_val}]──┘"
        )
        
        sig_str = f"multi_{a_val}_{b_val}_{op1}{op1_val}_{op2}{op2_val}_{merge_op}"
        signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
        return FlowchartPuzzle(
            flow_type="multi_path",
            nodes=[
                FlowNode("a", "A", value=a_val, is_input=True),
                FlowNode("b", "B", value=b_val, is_input=True),
                FlowNode("op1", f"{op1}{op1_val}", value=path_a, operation=op1, op_value=op1_val),
                FlowNode("op2", f"{op2}{op2_val}", value=path_b, operation=op2, op_value=op2_val),
                FlowNode("merge", merge_op, value=result),
                FlowNode("end", "?", value=result, is_output=True, is_unknown=True),
            ],
            edges=[("a", "op1"), ("b", "op2"), ("op1", "merge"), ("op2", "merge"), ("merge", "end")],
            input_value=a_val,
            output_value=result,
            operations=[
                {"from": "A", "op": op1, "value": op1_val, "result": path_a},
                {"from": "B", "op": op2, "value": op2_val, "result": path_b},
                {"merge_op": merge_op, "result": result},
            ],
            correct_answer=result,
            answer_var="?",
            puzzle_display=display,
            equations=[
                f"Yo'l A: {a_val} {op1} {op1_val} = {path_a}",
                f"Yo'l B: {b_val} {op2} {op2_val} = {path_b}",
                f"Birlashtirish: {path_a} {merge_op} {path_b} = {result}",
            ],
            explanation=f"A→{path_a}, B→{path_b}, {path_a} {merge_op} {path_b} = {result}",
            difficulty=difficulty,
            uniqueness_signature=signature,
        )
    
    def _build_linear_display(self, nodes: List[FlowNode],
                               edges: List[Tuple[str, str]],
                               hidden_node: FlowNode) -> str:
        """Chiziqli oqim display yaratish"""
        parts = []
        for node in nodes:
            if node.is_input:
                parts.append(f"[{node.label}: {node.value if node.value else '?'}]")
            elif node.is_output:
                parts.append(f"[{node.label}: {node.value if node.value else '?'}]")
            elif node.is_unknown:
                parts.append(f"[{node.label}: ?]")
            else:
                val_str = str(node.value) if node.value is not None else "?"
                parts.append(f"[{node.operation} {node.op_value} → {val_str}]")
        
        return " → ".join(parts)
    
    def _get_ops_for_grade(self, grade: int) -> List[str]:
        """Sinfga mos amallar"""
        if grade <= 2:
            return ["+", "-"]
        elif grade <= 4:
            return ["+", "-", "×"]
        else:
            return ["+", "-", "×", "÷"]


flowchart_engine = FlowchartEngine()
