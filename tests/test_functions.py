"""Tests for tree-sitter function extraction."""

from jj_supersede.functions import (
    diff_functions,
    extract_functions,
    functions_in_ranges,
    get_changed_ranges,
    parse_source,
)


PYTHON_SOURCE = '''\
def hello():
    print("hello")

def goodbye(name):
    print(f"bye {name}")

class Foo:
    def method(self):
        pass
'''

PYTHON_SOURCE_V2 = '''\
def hello():
    print("hello world")

def goodbye(name):
    print(f"bye {name}")

def new_func():
    return 42

class Foo:
    def method(self):
        pass
'''

RUST_SOURCE = '''\
fn main() {
    println!("hello");
}

fn helper(x: i32) -> i32 {
    x + 1
}
'''

JS_SOURCE = '''\
function greet(name) {
    return `Hello, ${name}!`;
}

function farewell(name) {
    return `Bye, ${name}!`;
}
'''


def test_extract_python_functions():
    fns = extract_functions(PYTHON_SOURCE, "example.py")
    names = [f.name for f in fns]
    assert "hello" in names
    assert "goodbye" in names
    assert "method" in names
    assert len(fns) == 3


def test_extract_rust_functions():
    fns = extract_functions(RUST_SOURCE, "main.rs")
    names = [f.name for f in fns]
    assert "main" in names
    assert "helper" in names
    assert len(fns) == 2


def test_extract_js_functions():
    fns = extract_functions(JS_SOURCE, "app.js")
    names = [f.name for f in fns]
    assert "greet" in names
    assert "farewell" in names
    assert len(fns) == 2


def test_unsupported_extension():
    fns = extract_functions("some content", "data.csv")
    assert fns == []


def test_parse_source():
    tree = parse_source(PYTHON_SOURCE, "example.py")
    assert tree is not None
    assert tree.root_node.type == "module"


def test_parse_unsupported():
    tree = parse_source("some content", "data.csv")
    assert tree is None


def test_changed_ranges():
    ranges = get_changed_ranges(PYTHON_SOURCE, PYTHON_SOURCE_V2, "example.py")
    assert len(ranges) > 0


def test_functions_in_ranges():
    fns = extract_functions(PYTHON_SOURCE_V2, "example.py")
    ranges = get_changed_ranges(PYTHON_SOURCE, PYTHON_SOURCE_V2, "example.py")
    affected = functions_in_ranges(fns, ranges)
    names = [f.name for f in affected]
    assert "hello" in names  # body changed


def test_diff_functions_modified():
    diff = diff_functions(PYTHON_SOURCE, PYTHON_SOURCE_V2, "example.py")
    assert diff.path == "example.py"
    modified_names = [old.name for old, _ in diff.modified]
    assert "hello" in modified_names  # body changed


def test_diff_functions_added():
    diff = diff_functions(PYTHON_SOURCE, PYTHON_SOURCE_V2, "example.py")
    added_names = [f.name for f in diff.added]
    assert "new_func" in added_names


def test_diff_functions_removed():
    diff = diff_functions(PYTHON_SOURCE_V2, PYTHON_SOURCE, "example.py")
    removed_names = [f.name for f in diff.removed]
    assert "new_func" in removed_names


def test_diff_functions_none_old():
    diff = diff_functions(None, PYTHON_SOURCE, "example.py")
    assert len(diff.added) == 3
    assert len(diff.removed) == 0
    assert len(diff.modified) == 0


def test_diff_functions_none_new():
    diff = diff_functions(PYTHON_SOURCE, None, "example.py")
    assert len(diff.added) == 0
    assert len(diff.removed) == 3
    assert len(diff.modified) == 0
