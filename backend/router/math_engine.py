"""Local mathematics engine for deterministic calculations."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import logging
import math
import operator
import re
from typing import Any

from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MathResult:
    """Structured authoritative result from the local math engine."""

    expression: str
    result: Any
    success: bool
    source: str = "python_math_engine"
    operation: str = "arithmetic"
    error: str | None = None


class MathEngine:
    """Safely handles local arithmetic before any LLM formatting."""

    OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def solve(self, text: str) -> dict[str, Any]:
        try:
            lowered = text.lower()
            expression = self._extract_expression(text)
            if "gcd" in lowered:
                nums = self._numbers(text)
                return self._answer(math.gcd(*nums), "gcd", expression)
            if "lcm" in lowered:
                nums = self._numbers(text)
                return self._answer(math.lcm(*nums), "lcm", expression)
            if "factorial" in lowered or "!" in text:
                nums = self._numbers(text)
                return self._answer(math.factorial(nums[0]), "factorial", expression)
            if "sqrt" in lowered or "square root" in lowered:
                nums = self._numbers(text)
                return self._answer(math.sqrt(nums[0]), "sqrt", expression)
            percentage = self._percentage_of(text)
            if percentage is not None:
                return self._answer(percentage, "percentage", expression)
            if "prime" in lowered:
                nums = self._numbers(text)
                value = nums[0]
                return self._answer(self._is_prime(value), "prime", expression)
            if self._looks_quadratic(lowered):
                roots = self._quadratic_roots(text)
                return self._answer(roots, "quadratic", expression)

            normalized = self._normalize_expression(expression)
            value = self._eval_ast(ast.parse(normalized, mode="eval").body)
            return self._answer(value, "arithmetic", expression)
        except ZeroDivisionError:
            LOGGER.warning("Local math engine rejected division by zero.")
            return error_response(
                "math",
                "solve",
                "Cannot divide by zero.",
                details=None,
            )
        except Exception as exc:
            LOGGER.warning("Local math engine could not solve query: %s", exc)
            return error_response("math", "solve", "Local math engine could not solve this.", details=repr(exc))

    @staticmethod
    def _answer(value: Any, operation: str, expression: str) -> dict[str, Any]:
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        result = MathResult(expression=expression, result=value, success=True, operation=operation)
        return success_response(
            "math",
            "solve",
            {
                "operation": result.operation,
                "expression": result.expression,
                "result": result.result,
                "source": result.source,
                "authoritative": True,
                "tool_name": "python_math_engine",
            },
            f"{result.expression} = {result.result}",
        )

    @staticmethod
    def _numbers(text: str) -> list[int]:
        nums = [int(item) for item in re.findall(r"-?\d+", text)]
        if not nums:
            raise ValueError("No numbers found.")
        return nums

    @staticmethod
    def _percentage_of(text: str) -> float | None:
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*%\s+of\s+(-?\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
        if not match:
            return None
        percent, value = (float(item) for item in match.groups())
        return value * percent / 100

    @staticmethod
    def _normalize_expression(text: str) -> str:
        text = text.replace("Ã—", "*").replace("Ã·", "/")
        return (
            text.replace("\u00d7", "*")
            .replace("Ã—", "*")
            .replace("x", "*")
            .replace("X", "*")
            .replace("\u00f7", "/")
            .replace("Ã·", "/")
            .replace("^", "**")
            .replace("%", "/100")
        )

    @staticmethod
    def _extract_expression(text: str) -> str:
        cleaned = text.strip().rstrip("?!.")
        cleaned = cleaned.replace("Ã—", "×").replace("Ã·", "÷")
        prefixes = (
            "explain how to calculate",
            "explain how to solve",
            "what is",
            "calculate",
            "compute",
            "solve",
        )
        lowered = cleaned.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return cleaned[len(prefix):].strip()
        match = re.search(r"-?\d[\d\s+\-*/xX\u00d7Ã—\u00f7Ã·%^().]*\d", cleaned)
        if match:
            return match.group(0).strip()
        return cleaned

    @staticmethod
    def _format_number(value: Any) -> str:
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _eval_ast(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self.OPS:
            return self.OPS[type(node.op)](self._eval_ast(node.left), self._eval_ast(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.OPS:
            return self.OPS[type(node.op)](self._eval_ast(node.operand))
        raise ValueError("Unsupported expression.")

    @staticmethod
    def _is_prime(value: int) -> bool:
        if value < 2:
            return False
        for divisor in range(2, int(math.sqrt(value)) + 1):
            if value % divisor == 0:
                return False
        return True

    @staticmethod
    def _looks_quadratic(text: str) -> bool:
        return "x^2" in text or "quadratic" in text

    @staticmethod
    def _quadratic_roots(text: str) -> tuple[float, float]:
        normalized = text.replace(" ", "")
        match = re.search(r"([+-]?\d*)x\^2([+-]\d*)x([+-]\d+)", normalized)
        if not match:
            raise ValueError("Unsupported quadratic format.")
        a_raw, b_raw, c_raw = match.groups()
        a = int(a_raw) if a_raw not in {"", "+"} else 1
        if a_raw == "-":
            a = -1
        b = int(b_raw) if b_raw not in {"+", "-"} else int(f"{b_raw}1")
        c = int(c_raw)
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            raise ValueError("Complex roots are not supported yet.")
        root = math.sqrt(discriminant)
        return ((-b + root) / (2 * a), (-b - root) / (2 * a))
