"""Bounded source/test navigation; static imports are not runtime proof."""

import ast
import hashlib
import re
from pathlib import Path

from .store import source_files


SUFFIXES = {'.py', '.js', '.jsx', '.ts', '.tsx', '.dart', '.cs', '.swift', '.go', '.rs',
            '.java', '.kt', '.kts', '.c', '.cc', '.cpp', '.h', '.hpp', '.html', '.css', '.sh'}
PRIVATE = {'.agents', '.codex', '.aws', '.ssh'}


def source_packet(store, task, features):
    root = store.task_source(task)
    terms = set(re.findall(r'[a-z][a-z0-9_]{3,}', (task['instructions'] + ' ' + ' '.join(task['criteria'])).lower()))
    entries = {path for feature in features for path in feature['code_entry_points']}
    nodes, declarations, skipped, consumed = {}, {}, 0, 0
    for path in source_files(root):
        relative = str(path.relative_to(root))
        if path.suffix not in SUFFIXES or PRIVATE & set(path.relative_to(root).parts):
            continue
        size = path.stat().st_size
        if path.is_symlink() or len(nodes) >= 500 or size > 256 * 1024 or consumed + size > 4 * 1024 * 1024:
            skipped += 1
            continue
        data = path.read_bytes()
        consumed += len(data)
        try:
            contents = data.decode('utf-8')
        except UnicodeError:
            skipped += 1
            continue
        symbols, imports, parser = [], [], 'metadata_only'
        if path.suffix == '.py':
            try:
                tree = ast.parse(contents)
                parser = 'python_ast'
                for item in ast.walk(tree):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        symbols.append({'name': item.name, 'line': item.lineno})
                    elif isinstance(item, ast.Import):
                        imports.extend(alias.name.replace('.', '/') for alias in item.names)
                    elif isinstance(item, ast.ImportFrom):
                        prefix = list(path.relative_to(root).parent.parts)
                        if item.level:
                            prefix = prefix[:len(prefix) - item.level + 1]
                        else:
                            prefix = []
                        module = '/'.join(prefix + (item.module or '').split('.')).rstrip('/')
                        imports.append(module)
                        imports.extend(module + '/' + alias.name for alias in item.names)
            except SyntaxError:
                parser = 'unparsed_python'
        elif path.suffix in {'.js', '.jsx', '.ts', '.tsx', '.dart'}:
            parser = 'import_regex_hint'
            for match in re.finditer(r'''(?:from\s+|import\s*(?:\(\s*)?|export\s+|part\s+|require\s*\(\s*)(["'])([^"']+)\1''', contents):
                target = match.group(2)
                if target.startswith('.'):
                    resolved = (path.parent / target).resolve()
                    if resolved.is_relative_to(root):
                        imports.append(str(resolved.relative_to(root)))
        is_test = bool({'tests', 'test', '__tests__', 'androidTest'} & set(path.relative_to(root).parts)
                       or path.name.startswith('test_') or '.test.' in path.name or '.spec.' in path.name
                       or path.stem.endswith('Test'))
        matched = sum(term in (relative + ' ' + ' '.join(item['name'] for item in symbols)).lower() for term in terms)
        nodes[relative] = {'path': relative, 'original_path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
                           'kind': 'test' if is_test else 'source', 'symbols': symbols[:40], 'parser': parser,
                           'relevance': 10 if relative in entries else matched}
        declarations[relative] = imports
    edges = []
    for origin, imports in declarations.items():
        for target in imports:
            suffix = Path(origin).suffix
            extensions = ('.py',) if suffix == '.py' else ('.dart',) if suffix == '.dart' else ('.ts', '.tsx', '.js', '.jsx')
            candidates = [target] + [target + extension for extension in extensions]
            candidates += [target + '/__init__.py'] if suffix == '.py' else [target + '/index.ts', target + '/index.js']
            if target.endswith('.js'):
                candidates += [target[:-3] + suffix for suffix in ('.ts', '.tsx')]
            destination = next((name for name in candidates if name in nodes and name != origin), None)
            if destination:
                edges.append({'from': origin, 'to': destination, 'kind': 'local_import', 'basis': nodes[origin]['parser']})
    for edge in edges:
        if nodes[edge['from']]['relevance'] >= 10 or nodes[edge['to']]['relevance'] >= 10:
            for path in (edge['from'], edge['to']):
                nodes[path]['relevance'] = max(5, nodes[path]['relevance'])
    ranked = sorted(nodes.values(), key=lambda item: (-item['relevance'], item['path']))
    selected = ranked[:24]
    paths = {item['path'] for item in selected}
    graph = sorted({(edge['from'], edge['to'], edge['basis']) for edge in edges if edge['from'] in paths and edge['to'] in paths})
    return {'version': 1, 'source_root': str(root), 'selected_files': selected,
            'dependency_graph': [{'from': origin, 'to': destination, 'kind': 'local_import', 'basis': basis}
                                 for origin, destination, basis in graph[:100]],
            'tests': [item for item in ranked if item['kind'] == 'test'][:12],
            'compression': 'ranked paths, symbols and hashes; original source remains accessible',
            'indexed_files': len(nodes), 'omitted_files': skipped + max(0, len(nodes) - len(selected)),
            'limitations': ['Static import edges guide navigation; they do not prove runtime behavior or complete call relationships.',
                            'Python uses AST imports; JS/TS/Dart use labeled syntax hints. Other languages retain source/test metadata.',
                            'The index is bounded to 500 files, 4 MiB total input, 24 selected files and 100 selected edges.']}
