from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

from .datalog import Atom, DatalogRule, Equality, BodyTerm, is_variable, validate_rule
from .errors import SpecForgeError


RIF_NS = "http://www.w3.org/2007/rif#"
NS = {"rif": RIF_NS}
ET.register_namespace("rif", RIF_NS)


def _tag(local: str) -> str:
    return f"{{{RIF_NS}}}{local}"


def _term(parent: ET.Element, value, *, iri: bool = False) -> None:
    element = ET.SubElement(parent, _tag("Var" if is_variable(value) else "Const"))
    if is_variable(value):
        element.text = value[1:]
    else:
        element.set("type", "http://www.w3.org/2007/rif#iri" if iri else "http://www.w3.org/2001/XMLSchema#string")
        element.text = str(value)


def _atom(parent: ET.Element, atom: Atom) -> None:
    element = ET.SubElement(parent, _tag("Atom"))
    op = ET.SubElement(element, _tag("op"))
    _term(op, f"https://specforge.dev/relation/{quote(atom.relation, safe='-._~')}", iri=True)
    args = ET.SubElement(element, _tag("args"), {"ordered": "yes"})
    for value in atom.terms:
        _term(args, value)


def export_rules(rules: list[DatalogRule]) -> str:
    """Serialize the supported positive Datalog subset as RIF Core XML."""
    document = ET.Element(_tag("Document"))
    payload = ET.SubElement(document, _tag("payload"))
    group = ET.SubElement(payload, _tag("Group"))
    for rule in sorted(rules, key=lambda item: (item.id, item.version, repr(item.body))):
        validate_rule(rule)
        sentence = ET.SubElement(group, _tag("sentence"))
        forall = ET.SubElement(sentence, _tag("Forall"))
        variables = sorted({
            item[1:]
            for atom in (rule.head, *(term for term in rule.body if isinstance(term, Atom)))
            for item in atom.terms if is_variable(item)
        } | {
            item[1:] for term in rule.body if isinstance(term, Equality)
            for item in (term.left, term.right) if is_variable(item)
        })
        for variable in variables:
            declare = ET.SubElement(forall, _tag("declare"))
            _term(declare, f"${variable}")
        formula = ET.SubElement(forall, _tag("formula"))
        implies = ET.SubElement(formula, _tag("Implies"))
        identifier = ET.SubElement(implies, _tag("id"))
        _term(identifier, f"https://specforge.dev/rif-rule/{quote(rule.id, safe='-._~')}/{quote(rule.version, safe='-._~')}", iri=True)
        if_part = ET.SubElement(implies, _tag("if"))
        body_parent = if_part
        conjunction = None
        if len(rule.body) != 1:
            conjunction = ET.SubElement(if_part, _tag("And"))
        for term in rule.body:
            body_parent = ET.SubElement(conjunction, _tag("formula")) if conjunction is not None else if_part
            if isinstance(term, Atom):
                _atom(body_parent, term)
            else:
                equal = ET.SubElement(body_parent, _tag("Equal"))
                left, right = ET.SubElement(equal, _tag("left")), ET.SubElement(equal, _tag("right"))
                _term(left, term.left)
                _term(right, term.right)
        then_part = ET.SubElement(implies, _tag("then"))
        _atom(then_part, rule.head)
    ET.indent(document, space="  ")
    return ET.tostring(document, encoding="unicode", xml_declaration=True) + "\n"


def _read_term(element: ET.Element):
    child = next(iter(element)) if element.tag not in {_tag("Var"), _tag("Const")} else element
    if child.tag == _tag("Var"):
        return f"${child.text or ''}"
    if child.tag == _tag("Const"):
        return child.text or ""
    raise SpecForgeError("SF3201", "RIF", "/", f"unsupported term {child.tag}")


def _read_atom(element: ET.Element) -> Atom:
    relation = _read_term(element.find("rif:op", NS))
    if is_variable(relation):
        raise SpecForgeError("SF1204", "RIF", "/Atom/op", "variable predicates are forbidden")
    args = element.find("rif:args", NS)
    children = list(args) if args is not None else []
    relation_name = unquote(str(relation).rsplit("/relation/", 1)[-1])
    return Atom(relation_name, tuple(_read_term(child) for child in children))


def import_rules(source: str | Path) -> list[DatalogRule]:
    """Parse only the documented RIF Core subset; reject unknown constructs."""
    raw = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise SpecForgeError("SF3202", "RIF", "/", "DTD and XML entities are forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SpecForgeError("SF3201", "RIF", "/", str(exc)) from exc
    rules: list[DatalogRule] = []
    if root.find(".//rif:Import", NS) is not None:
        raise SpecForgeError("SF3202", "RIF", "/Import", "remote RIF imports are forbidden")
    for implies in root.findall(".//rif:Implies", NS):
        head_element = implies.find("rif:then/rif:Atom", NS)
        if_element = implies.find("rif:if", NS)
        if head_element is None or if_element is None:
            raise SpecForgeError("SF3201", "RIF", "/Implies", "only positive Core implications are supported")
        body: list[BodyTerm] = []
        conjunction = if_element.find("rif:And", NS)
        containers = conjunction.findall("rif:formula", NS) if conjunction is not None else [if_element]
        for container in containers:
            if len(container) != 1:
                raise SpecForgeError("SF3201", "RIF", "/Implies/if", "each formula must contain one condition")
            child = next(iter(container))
            if child.tag == _tag("Atom"):
                body.append(_read_atom(child))
            elif child.tag == _tag("Equal"):
                body.append(Equality(_read_term(child.find("rif:left", NS)), _read_term(child.find("rif:right", NS))))
            else:
                raise SpecForgeError("SF3201", "RIF", "/Implies/if", f"unsupported construct {child.tag}")
        encoded = str(_read_term(implies.find("rif:id", NS))).rsplit("/rif-rule/", 1)[-1]
        encoded_id, _, encoded_version = encoded.rpartition("/")
        rule = DatalogRule(unquote(encoded_id), unquote(encoded_version), _read_atom(head_element), tuple(body))
        validate_rule(rule)
        rules.append(rule)
    return rules
