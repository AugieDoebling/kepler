import ast
import math
import operator
from datetime import datetime

import requests

# Wikipedia asks API clients to say who they are, a generic name is enough
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_USER_AGENT = "KeplerRobot/1.0 (home robot; python-requests)"
WIKIPEDIA_TIMEOUT_S = 15
# Enough for the article's opening section without flooding a small model's context
MAX_WIKIPEDIA_CHARS = 3000


def get_time() -> str:
    """
    Get the current date and time. Use this whenever the answer depends on today's date, the day of the week or the time.
    """
    now = datetime.now().astimezone()
    return now.strftime("%A %d %B %Y, %I:%M %p %Z").replace(" 0", " ")


# Only plain arithmetic and these functions, so nothing the LLM writes can run arbitrary code
BINARY_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
FUNCTIONS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": math.atan, "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "radians": math.radians, "degrees": math.degrees, "floor": math.floor, "ceil": math.ceil,
    "round": round, "abs": abs, "min": min, "max": max,
}
CONSTANTS = {"pi": math.pi, "e": math.e}
# A huge power like 9**9**9 would hang the robot working it out
MAX_EXPONENT = 1000


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise ValueError("That power is too big to work out.")
        return BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS
            and not node.keywords):
        return FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise ValueError(f"Can't work out {ast.unparse(node)!r}, only numbers, + - * / // % **, and maths functions are allowed.")


def calculate(expression: str) -> str:
    """
    Work out a maths expression exactly. Use this for any arithmetic, percentages, tips or unit conversions rather than doing it in your head.

    :param expression: The expression in Python syntax, such as "18 * 0.2" or "sqrt(2) * 10". Write powers as **. Functions: sqrt, sin, cos, tan, log, log10, exp, round, abs, min, max, floor, ceil. Constants: pi, e.
    """
    # Models often write powers the usual way rather than Python's
    expression = expression.replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        result = _evaluate(ast.parse(expression.strip(), mode="eval"))
    except SyntaxError:
        return f"Error: {expression!r} is not a valid expression."
    except ZeroDivisionError:
        return "Error: division by zero."
    except (ValueError, TypeError, OverflowError) as e:
        return f"Error: {e}"
    if isinstance(result, float):
        if result.is_integer() and abs(result) < 1e15:
            result = int(result)
        else:
            result = round(result, 10)
    return f"{expression} = {result}"


def wikipedia_lookup(topic: str) -> str:
    """
    Look up a person, place, thing or event on Wikipedia and get the opening of its article. Better than a web search for facts and background.

    :param topic: What to look up, such as "Mars" or "Golden Gate Bridge".
    """
    # One request finds the best matching article and returns its introduction as plain text
    response = requests.get(WIKIPEDIA_API, params={
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": topic, "gsrlimit": 1,
        "prop": "extracts", "exintro": 1, "explaintext": 1, "redirects": 1,
    }, headers={"User-Agent": WIKIPEDIA_USER_AGENT}, timeout=WIKIPEDIA_TIMEOUT_S)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    if not pages or not pages[0].get("extract"):
        return f"Wikipedia has no article about {topic!r}."
    page = pages[0]
    text = page["extract"].strip()
    if len(text) > MAX_WIKIPEDIA_CHARS:
        text = text[:MAX_WIKIPEDIA_CHARS].rsplit(" ", 1)[0] + " [truncated]"
    return f"{page['title']} (Wikipedia):\n{text}"
