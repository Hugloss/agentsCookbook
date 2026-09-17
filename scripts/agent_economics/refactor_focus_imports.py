import ast
from collections import defaultdict
from pathlib import Path

from .refactor_focus_paths import module_path_for_file, source_module_path


def is_first_party_module(module: str, package_names: set[str]) -> bool:
    return any(
        module == name or module.startswith(f"{name}.") for name in package_names
    )


def parse_internal_imported_modules(
    *,
    path: Path,
    root: Path,
    current_package_name: str,
    package_names: set[str],
) -> set[str]:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, ValueError, OSError):
        return set()

    try:
        current_module_parts = module_path_for_file(
            path=path,
            root=root,
            package_name=current_package_name,
        ).split(".")
    except ValueError:
        current_module_parts = []

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.strip()
                if is_first_party_module(name, package_names):
                    modules.add(name)
        elif isinstance(node, ast.ImportFrom):
            base_module = resolve_import_from_module(
                node=node,
                current_module_parts=current_module_parts,
                current_is_package=path.name == "__init__.py",
            )
            if not base_module or not is_first_party_module(base_module, package_names):
                continue
            modules.add(base_module)
            for alias in node.names:
                name = alias.name.strip()
                if name and name != "*":
                    modules.add(f"{base_module}.{name}")
    return modules


def resolve_import_from_module(
    *,
    node: ast.ImportFrom,
    current_module_parts: list[str],
    current_is_package: bool,
) -> str:
    module = (node.module or "").strip()
    level = getattr(node, "level", 0)
    if level <= 0:
        return module
    if not current_module_parts:
        return module

    package_parts = (
        current_module_parts
        if current_is_package
        else current_module_parts[:-1]
    )
    ascend = level - 1
    if ascend > len(package_parts):
        return ""
    base_parts = package_parts[: len(package_parts) - ascend] if ascend else package_parts
    if module:
        return ".".join((*base_parts, module))
    return ".".join(base_parts)


def build_import_index(
    *,
    files: list[Path],
    root: Path,
    current_package_name: str,
    package_names: set[str],
) -> dict[str, set[Path]]:
    index: dict[str, set[Path]] = defaultdict(set)
    for file_path in files:
        for module in parse_internal_imported_modules(
            path=file_path,
            root=root,
            current_package_name=current_package_name,
            package_names=package_names,
        ):
            index[module].add(file_path)
    return dict(index)


def internal_imports_for_file(
    *,
    path: Path,
    root: Path,
    current_package_name: str,
    package_names: set[str],
) -> set[str]:
    return parse_internal_imported_modules(
        path=path,
        root=root,
        current_package_name=current_package_name,
        package_names=package_names,
    )


def parse_dynamic_loaded_source_modules(
    *,
    path: Path,
    source_root: Path,
    package_name: str,
) -> set[str]:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, ValueError, OSError):
        return set()

    env: dict[str, Path] = {}
    modules: set[str] = set()
    current_file = path.resolve()

    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            evaluated = evaluate_path_expression(
                node.value,
                current_file=current_file,
                env=env,
            )
            if evaluated is not None:
                env[node.targets[0].id] = evaluated
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not is_spec_from_file_location_call(call):
            continue
        if len(call.args) < 2:
            continue
        loaded_path = evaluate_path_expression(
            call.args[1],
            current_file=current_file,
            env=env,
        )
        if loaded_path is None:
            continue
        try:
            module = source_module_path(
                source_path=loaded_path.resolve(),
                source_root=source_root.resolve(),
                package_name=package_name,
            )
        except ValueError:
            continue
        modules.add(module)
    return modules


def is_spec_from_file_location_call(node: ast.Call) -> bool:
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == "spec_from_file_location"


def evaluate_path_expression(
    node: ast.AST,
    *,
    current_file: Path,
    env: dict[str, Path],
) -> Path | None:
    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return current_file
        return env.get(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return Path(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = evaluate_path_expression(node.left, current_file=current_file, env=env)
        right = evaluate_path_expression(node.right, current_file=current_file, env=env)
        if left is None or right is None:
            return None
        return left / right
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        value = evaluate_path_expression(node.value, current_file=current_file, env=env)
        if value is None:
            return None
        return value.parent
    if isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "Path"
            and len(node.args) == 1
        ):
            return evaluate_path_expression(
                node.args[0],
                current_file=current_file,
                env=env,
            )
        if isinstance(node.func, ast.Attribute) and node.func.attr == "resolve":
            value = evaluate_path_expression(
                node.func.value,
                current_file=current_file,
                env=env,
            )
            if value is None:
                return None
            return value.resolve()
    return None
