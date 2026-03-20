"""Extract function definitions from source code using tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tree_sitter_javascript as ts_js
import tree_sitter_python as ts_py
import tree_sitter_rust as ts_rust
from tree_sitter import Language, Parser, Tree


# Language registry: extension -> (language, function node types, name extraction)
_LANGUAGES: dict[str, tuple[Language, list[str]]] = {}


def _init_languages() -> None:
    if _LANGUAGES:
        return
    _LANGUAGES[".py"] = (Language(ts_py.language()), ["function_definition"])
    _LANGUAGES[".rs"] = (Language(ts_rust.language()), ["function_item"])
    _LANGUAGES[".js"] = (Language(ts_js.language()), ["function_declaration", "method_definition"])
    _LANGUAGES[".ts"] = (Language(ts_js.language()), ["function_declaration", "method_definition"])
    _LANGUAGES[".tsx"] = (Language(ts_js.language()), ["function_declaration", "method_definition"])
    _LANGUAGES[".jsx"] = (Language(ts_js.language()), ["function_declaration", "method_definition"])


def _get_language(path: str) -> tuple[Language, list[str]] | None:
    _init_languages()
    ext = Path(path).suffix
    return _LANGUAGES.get(ext)


@dataclass(frozen=True)
class FunctionDef:
    name: str
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    body_hash: int  # hash of the function body bytes for quick comparison

    @property
    def span(self) -> tuple[int, int]:
        return (self.start_byte, self.end_byte)


def _extract_name(node) -> str:
    """Extract function name from a function node."""
    for child in node.children:
        if child.type in ("identifier", "name"):
            return child.text.decode("utf-8")
    return "<anonymous>"


def parse_source(source: str, path: str) -> Tree | None:
    """Parse source code into a tree-sitter Tree."""
    lang_info = _get_language(path)
    if lang_info is None:
        return None
    lang, _ = lang_info
    parser = Parser(lang)
    return parser.parse(source.encode("utf-8"))


def extract_functions(source: str, path: str) -> list[FunctionDef]:
    """Extract all top-level and nested function definitions from source."""
    lang_info = _get_language(path)
    if lang_info is None:
        return []

    lang, node_types = lang_info
    parser = Parser(lang)
    tree = parser.parse(source.encode("utf-8"))
    source_bytes = source.encode("utf-8")

    functions: list[FunctionDef] = []
    _walk_for_functions(tree.root_node, node_types, source_bytes, functions)
    return functions


def _walk_for_functions(
    node, node_types: list[str], source_bytes: bytes, out: list[FunctionDef]
) -> None:
    """Recursively walk tree to find function nodes."""
    if node.type in node_types:
        name = _extract_name(node)
        body = source_bytes[node.start_byte : node.end_byte]
        out.append(
            FunctionDef(
                name=name,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                body_hash=hash(body),
            )
        )
    for child in node.children:
        _walk_for_functions(child, node_types, source_bytes, out)


def get_changed_ranges(old_source: str, new_source: str, path: str) -> list[tuple[int, int]]:
    """Get byte ranges that changed between two versions of a file."""
    lang_info = _get_language(path)
    if lang_info is None:
        return []

    lang, _ = lang_info
    parser = Parser(lang)
    old_tree = parser.parse(old_source.encode("utf-8"))
    new_tree = parser.parse(new_source.encode("utf-8"))

    ranges = old_tree.changed_ranges(new_tree)
    return [(r.start_byte, r.end_byte) for r in ranges]


def functions_in_ranges(
    functions: list[FunctionDef], ranges: list[tuple[int, int]]
) -> list[FunctionDef]:
    """Return functions that overlap with any of the given byte ranges."""
    result = []
    for func in functions:
        for r_start, r_end in ranges:
            if func.start_byte < r_end and func.end_byte > r_start:
                result.append(func)
                break
    return result


@dataclass(frozen=True)
class FunctionDiff:
    """Diff result for functions between two file versions."""

    path: str
    added: list[FunctionDef]  # in new, not in old
    removed: list[FunctionDef]  # in old, not in new
    modified: list[tuple[FunctionDef, FunctionDef]]  # (old, new) — same name, different body


def diff_functions(old_source: str | None, new_source: str | None, path: str) -> FunctionDiff:
    """Compare function definitions between two versions of a file."""
    old_fns = extract_functions(old_source, path) if old_source else []
    new_fns = extract_functions(new_source, path) if new_source else []

    old_by_name = {f.name: f for f in old_fns}
    new_by_name = {f.name: f for f in new_fns}

    added = [f for name, f in new_by_name.items() if name not in old_by_name]
    removed = [f for name, f in old_by_name.items() if name not in new_by_name]
    modified = [
        (old_by_name[name], new_by_name[name])
        for name in old_by_name
        if name in new_by_name and old_by_name[name].body_hash != new_by_name[name].body_hash
    ]

    return FunctionDiff(path=path, added=added, removed=removed, modified=modified)


def supported_extensions() -> set[str]:
    _init_languages()
    return set(_LANGUAGES.keys())
