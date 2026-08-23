from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SUPPORTED_AUTHORING_SUFFIXES = (".ttl", ".trig", ".rq", ".rif.xml", ".prolog")

RDF_PREDICATE_EXPLANATIONS = {
    "a": "Diese Aussage legt den formalen Typ der Ressource fest.",
    "dcterms:identifier": "Diese Aussage legt die stabile Kennung der Ressource fest.",
    "dcterms:hasVersion": "Diese Aussage pinnt die konkrete Version der Ressource.",
    "dcterms:title": "Diese Aussage gibt der Ressource einen verständlichen Titel.",
    "dcterms:description": "Diese Aussage beschreibt die fachliche Bedeutung der Ressource.",
    "dcterms:requires": "Diese Aussage benennt eine notwendige Package-Abhängigkeit.",
    "sf:usesStack": "Diese Aussage verbindet das Product mit seinem technischen Stack.",
    "sf:defines": "Diese Aussage verbindet das Product mit einer definierten Entity.",
    "sf:offers": "Diese Aussage verbindet das Product mit einer angebotenen Operation.",
    "sf:declaresRequirement": "Diese Aussage verbindet das Product mit einem direkt erklärten Requirement.",
    "sf:hasField": "Diese Aussage ordnet der Entity eines ihrer Felder zu.",
    "sf:valueType": "Diese Aussage legt den Wertetyp des Feldes fest.",
    "sf:action": "Diese Aussage benennt die positive fachliche Aktion der Operation.",
    "sf:actsOn": "Diese Aussage benennt die von der Operation bearbeitete Ressource.",
    "sf:returns": "Diese Aussage benennt die von der Operation zurückgegebene Ressource.",
    "sf:actor": "Diese Aussage benennt die handelnde Entity der Operation.",
    "sf:requirement": "Diese Aussage verweist auf die allgemeine Requirement Definition.",
    "sf:appliesTo": "Diese Aussage benennt das konkrete Target des Requirements.",
    "sf:verifiedBy": "Diese Aussage verbindet das Requirement mit einer ausführbaren Verification.",
    "sf:satisfies": "Diese Aussage benennt das vom Pattern erfüllte Requirement.",
}


@dataclass(frozen=True)
class CommentViolation:
    path: Path
    line: int
    message: str

    def render(self, root: Path | None = None) -> str:
        display = self.path
        if root is not None:
            try:
                display = self.path.relative_to(root)
            except ValueError:
                pass
        return f"{display}:{self.line}: {self.message}"


def _meaningful_comment(value: str) -> bool:
    text = re.sub(r"^(#|%|<!--)|(-->)$", "", value.strip()).strip()
    if not text or "TODO" in text.upper():
        return False
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", text)
    return len(words) >= 4


def _previous_comment(lines: list[str], index: int, marker: str = "#") -> bool:
    cursor = index - 1
    if cursor < 0:
        return False
    value = lines[cursor].strip()
    return value.startswith(marker) and _meaningful_comment(value)


def _compact_predicate_positions(line: str) -> list[int]:
    """Find semicolons followed by another top-level RDF assertion."""
    positions: list[int] = []
    quote = None
    escaped = False
    angle = square = paren = 0
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if quote:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "<":
            angle += 1
        elif char == ">" and angle:
            angle -= 1
        elif not angle:
            if char == "[":
                square += 1
            elif char == "]":
                square -= 1
            elif char == "(":
                paren += 1
            elif char == ")":
                paren -= 1
            elif char == ";" and square == 0 and paren == 0 and line[index + 1:].strip():
                positions.append(index)
    return positions


def _lint_rdf(path: Path, lines: list[str]) -> list[CommentViolation]:
    violations: list[CommentViolation] = []
    in_multiline = False
    depth = 0
    for index, raw in enumerate(lines):
        line = raw.strip()
        if '"""' in line or "'''" in line:
            in_multiline = not in_multiline
        if in_multiline or not line or line.startswith(("#", "@prefix", "@base", "PREFIX", "BASE")):
            continue
        graph_start = bool(re.match(r"(?:GRAPH\s+)?(?:<[^>]+>|[\w-]+:[\w.-]+)\s*\{\s*$", line, re.I))
        semantic_line = (
            not graph_start
            and not re.match(r"^[\]\)};]+\s*[.;,]?$", line)
            and (depth > 0 or path.suffix == ".ttl")
        )
        if (graph_start or semantic_line) and not _previous_comment(lines, index):
            kind = "Named Graph" if graph_start else "RDF-Aussage"
            violations.append(CommentViolation(path, index + 1, f"{kind} benötigt einen verständlichen Lernkommentar"))
        if semantic_line and _compact_predicate_positions(line):
            violations.append(CommentViolation(
                path, index + 1,
                "Mehrere RDF-Aussagen müssen auf getrennten, jeweils kommentierten Zeilen stehen",
            ))
        depth += line.count("{") - line.count("}")
    return violations


def _lint_sparql(path: Path, lines: list[str]) -> list[CommentViolation]:
    violations: list[CommentViolation] = []
    first_query = next((i for i, line in enumerate(lines) if re.match(r"\s*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", line, re.I)), None)
    if first_query is not None and not _previous_comment(lines, first_query):
        violations.append(CommentViolation(path, first_query + 1, "SPARQL Query benötigt einen kommentierten Zweck"))
    for index, raw in enumerate(lines):
        if re.search(r"\b(WHERE|OPTIONAL|UNION|GRAPH)\b[^#]*\{", raw, re.I) and not _previous_comment(lines, index):
            violations.append(CommentViolation(path, index + 1, "SPARQL Graph Pattern benötigt einen Lernkommentar"))
        line = raw.strip()
        statement = (
            re.match(r"(?:<[^>]+>|\?\w+|[\w-]+:[\w.-]+)\s+", line)
            or re.match(r"(?:FILTER|BIND|VALUES)\b", line, re.I)
        )
        if statement and not line.upper().startswith(("SELECT ", "ASK ", "CONSTRUCT ", "DESCRIBE ")):
            if not _previous_comment(lines, index):
                violations.append(CommentViolation(path, index + 1, "SPARQL-Aussage benötigt einen Lernkommentar"))
    return violations


def _lint_prolog(path: Path, lines: list[str]) -> list[CommentViolation]:
    violations: list[CommentViolation] = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if (":-" in line or re.match(r"[a-z][\w-]*\s*\(", line)) and not _previous_comment(lines, index, "%"):
            violations.append(CommentViolation(path, index + 1, "Rule oder Literal benötigt einen verständlichen %-Lernkommentar"))
    return violations


def _lint_rif(path: Path, source: str) -> list[CommentViolation]:
    violations: list[CommentViolation] = []
    for match in re.finditer(r"<(?:\w+:)?Implies\b", source):
        prefix = source[:match.start()]
        line = prefix.count("\n") + 1
        preceding = re.search(r"<!--(.*?)-->\s*$", prefix, re.S)
        if preceding is None or not _meaningful_comment(preceding.group(0)):
            violations.append(CommentViolation(path, line, "RIF Rule benötigt unmittelbar davor einen XML-Lernkommentar"))
    for match in re.finditer(r"<(?:\w+:)?(?:Atom|Equal)\b", source):
        prefix = source[:match.start()]
        line = prefix.count("\n") + 1
        preceding = re.search(r"<!--(.*?)-->\s*$", prefix, re.S)
        if preceding is None or not _meaningful_comment(preceding.group(0)):
            violations.append(CommentViolation(path, line, "RIF Head oder Bedingungsatom benötigt einen XML-Lernkommentar"))
    return violations


def lint_comments(path: Path) -> list[CommentViolation]:
    """Validate the learning-comment contract for one file or directory."""
    path = path.resolve()
    files = [path] if path.is_file() else sorted(
        item for item in path.rglob("*")
        if item.is_file() and any(item.name.endswith(suffix) for suffix in SUPPORTED_AUTHORING_SUFFIXES)
    )
    violations: list[CommentViolation] = []
    for source_path in files:
        source = source_path.read_text(encoding="utf-8")
        lines = source.splitlines()
        if source_path.name.endswith((".ttl", ".trig")):
            violations.extend(_lint_rdf(source_path, lines))
        elif source_path.name.endswith(".rq"):
            violations.extend(_lint_sparql(source_path, lines))
        elif source_path.name.endswith(".rif.xml"):
            violations.extend(_lint_rif(source_path, source))
        elif source_path.name.endswith(".prolog"):
            violations.extend(_lint_prolog(source_path, lines))
    return violations


def add_missing_rdf_comments(path: Path) -> int:
    """Make a generated migration result comply without changing its RDF graph."""
    original = path.read_text(encoding="utf-8").splitlines()
    expanded: list[str] = []
    split_count = 0
    for line in original:
        positions = _compact_predicate_positions(line)
        if not positions:
            expanded.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        starts = [0, *(position + 1 for position in positions)]
        ends = [position + 1 for position in positions] + [len(line)]
        fragments = [line[start:end].strip() for start, end in zip(starts, ends)]
        expanded.append(indent + fragments[0])
        expanded.extend(indent + "  " + fragment for fragment in fragments[1:])
        split_count += len(fragments) - 1
    if split_count:
        path.write_text("\n".join(expanded) + "\n", encoding="utf-8")
    violations = {
        item.line for item in lint_comments(path)
        if item.path == path.resolve() and "RDF-Aussage" in item.message
    }
    if not violations:
        return split_count
    lines = path.read_text(encoding="utf-8").splitlines()
    rendered: list[str] = []
    for number, line in enumerate(lines, 1):
        if number in violations:
            tokens = re.findall(r"(?:<[^>]+>|[\w-]+:[\w.-]+|\ba\b)", line.strip())
            predicate = next((token for token in tokens[:2] if token in RDF_PREDICATE_EXPLANATIONS), None)
            explanation = RDF_PREDICATE_EXPLANATIONS.get(
                predicate or "",
                "Dieser Wert gehört zur unmittelbar zuvor benannten fachlichen Beziehung.",
            )
            indent = line[: len(line) - len(line.lstrip())]
            rendered.append(f"{indent}# {explanation}")
        rendered.append(line)
    path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
    return split_count + len(violations)
