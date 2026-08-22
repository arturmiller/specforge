from __future__ import annotations

from pathlib import Path
import json
import subprocess

import typer

from .compiler import Compiler
from .errors import SpecForgeError
from .io import write_if_changed
from .model import ResolvedSpec

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def root() -> Path:
    return Path.cwd()


def _read_resolved(path: Path) -> ResolvedSpec:
    return ResolvedSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _read_revision(value: Path, product: str) -> ResolvedSpec:
    if value.exists():
        return _read_resolved(value)
    product_id = Path(product).name
    repository_path = f"generated/{product_id}/resolved-spec.json"
    try:
        raw = subprocess.check_output(["git", "show", f"{value}:{repository_path}"], cwd=root(), text=True, encoding="utf-8", stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot load resolved spec from path or Git revision {value}") from exc
    return ResolvedSpec.model_validate_json(raw)


def fail(exc: Exception) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(1)


@app.command()
def resolve(product: str) -> None:
    """Resolve product and knowledge into a canonical system specification."""
    try:
        result = Compiler(root()).resolve(product)
        typer.echo(f"Resolved {result.product.id}@{result.product.version}")
        typer.echo(f"Requirements: {len(result.requirements)}")
        typer.echo(f"Content hash: {result.content_hash}")
    except (SpecForgeError, OSError) as exc:
        fail(exc)


@app.command()
def explain(
    requirement: str,
    product: str = typer.Option(..., "--product"),
    target: str | None = typer.Option(None, "--target", help="Typed target, for example operation:read_event."),
    group_by: str | None = typer.Option(None, "--group-by", help="Projection: target.type, rule, resource, or fact.<predicate>."),
) -> None:
    """Explain why a requirement applies."""
    try:
        typer.echo(Compiler(root()).explain(product, requirement, target=target, group_by=group_by), nl=False)
    except (SpecForgeError, OSError) as exc:
        fail(exc)


@app.command()
def generate(product: str) -> None:
    """Generate the selected application implementation."""
    try:
        from .generation import generate_product
        result = Compiler(root()).resolve(product)
        manifest = generate_product(root(), result)
        typer.echo(f"Generated {result.product.id}: {manifest}")
    except (SpecForgeError, OSError) as exc:
        fail(exc)


@app.command("diff")
def diff_command(
    product: str,
    from_revision: Path = typer.Option(..., "--from", help="Resolved-spec JSON used as the base revision."),
    to_revision: Path | None = typer.Option(None, "--to", help="Resolved-spec JSON used as the target; defaults to current inputs."),
) -> None:
    """Show a semantic V2 diff of typed targets."""
    try:
        from .v2 import semantic_diff

        before = _read_revision(from_revision, product)
        after = _read_revision(to_revision, product) if to_revision else Compiler(root()).resolve(product, write=False)
        result = semantic_diff(before, after)
        typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2))
    except (SpecForgeError, OSError, ValueError) as exc:
        fail(exc)


@app.command("plan")
def plan_command(
    product: str,
    base: Path | None = typer.Option(None, "--base", help="Previous resolved-spec JSON; defaults to the last generated spec."),
    format: str = typer.Option("text", "--format", help="text or json"),
    explain: str | None = typer.Option(None, "--explain", help="Explain a consolidated obligation by ID."),
) -> None:
    """Create a deterministic V2 implementation plan and work order."""
    try:
        from .v2 import build_plan

        generated = root() / "generated" / Path(product).name / "resolved-spec.json"
        base_path = base or generated
        before = _read_resolved(base_path) if base_path.exists() else Compiler(root()).resolve(product, write=False)
        after = Compiler(root()).resolve(product)
        plan, order = build_plan(root(), before, after)
        if explain:
            obligation = next((item for item in plan.obligations if item.id == explain), None)
            if obligation is None:
                raise ValueError(f"obligation not found: {explain}")
            typer.echo(json.dumps(obligation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2))
            return
        if format == "json":
            typer.echo(json.dumps({"plan": plan.model_dump(mode="json"), "work_order": order.model_dump(mode="json")}, ensure_ascii=False, sort_keys=True, indent=2))
        elif format == "text":
            typer.echo(f"Plan {plan.product}: {len(plan.targets)} targets, {len(plan.obligations)} obligations")
            typer.echo(f"Work order: {order.id} ({order.content_hash})")
        else:
            raise ValueError("--format must be text or json")
    except (SpecForgeError, OSError, ValueError) as exc:
        fail(exc)


@app.command("implement")
def implement_command(
    product: str,
    agent: str = typer.Option("codex", "--agent"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    base: Path | None = typer.Option(None, "--base"),
) -> None:
    """Execute a hash-bound work order through an agent adapter and gates."""
    try:
        from .agents.codex import CodexAdapter
        from .runs import RunManager
        from .v2 import build_plan

        if agent != "codex":
            raise ValueError("V2 currently supports --agent codex")
        generated = root() / "generated" / Path(product).name / "resolved-spec.json"
        base_path = base or generated
        before = _read_resolved(base_path) if base_path.exists() else Compiler(root()).resolve(product, write=False)
        after = Compiler(root()).resolve(product)
        _, order = build_plan(root(), before, after)
        if dry_run:
            typer.echo(json.dumps(order.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2))
            return
        result = RunManager(root()).execute(order, CodexAdapter())
        typer.echo(f"{result.id}: {result.work_order_status.value}")
        if result.work_order_status.value != "ACCEPTED":
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (SpecForgeError, OSError, ValueError, RuntimeError) as exc:
        fail(exc)


@app.command("runs")
def runs_command(product: str) -> None:
    """List versioned agent runs for a product."""
    directory = root() / "runs" / Path(product).name
    if not directory.exists():
        return
    for path in sorted(directory.glob("*/agent-result.json"), reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        typer.echo(f"{data['id']} {data['work_order_status']} {data['model']} {data['ended_at']}")


@app.command("show-run")
def show_run_command(run_id: str) -> None:
    """Show a run, its changes, gates, and evidence."""
    matches = list((root() / "runs").glob(f"*/{run_id}/agent-result.json"))
    if len(matches) != 1:
        fail(ValueError(f"run not found: {run_id}"))
    typer.echo(matches[0].read_text(encoding="utf-8"), nl=False)


@app.command("repair")
def repair_command(run_id: str, attempt: int = typer.Option(1, "--attempt", min=1)) -> None:
    """Create a scope-preserving repair work order from a rejected run."""
    try:
        from .runs import AgentRunResult, create_repair_order
        from .v2 import AgentWorkOrder

        directories = list((root() / "runs").glob(f"*/{run_id}"))
        if len(directories) != 1:
            raise ValueError(f"run not found: {run_id}")
        directory = directories[0]
        run = AgentRunResult.model_validate(json.loads((directory / "agent-result.json").read_text(encoding="utf-8")))
        order = AgentWorkOrder.model_validate(json.loads((directory / "work-order.json").read_text(encoding="utf-8")))
        if run.work_order_status.value != "REJECTED":
            raise ValueError("only rejected runs can be repaired")
        repair = create_repair_order(order, run, attempt)
        destination = directory / f"repair-{attempt}-work-order.json"
        from .io import pretty_json, write_if_changed

        write_if_changed(destination, pretty_json(repair.model_dump(mode="json")))
        typer.echo(str(destination))
    except (OSError, ValueError) as exc:
        fail(exc)


@app.command()
def validate(product: str) -> None:
    """Execute mandatory machine verifications."""
    try:
        from .verification import validate_product
        result = validate_product(root(), product)
        typer.echo(result.summary)
        if not result.passed:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (SpecForgeError, OSError, RuntimeError) as exc:
        fail(exc)


@app.command()
def evidence(product: str) -> None:
    """Validate and emit a schema-valid evidence bundle."""
    try:
        from .verification import validate_product
        result = validate_product(root(), product)
        typer.echo(str(result.evidence_path))
        if not result.passed:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (SpecForgeError, OSError, RuntimeError) as exc:
        fail(exc)


@app.command()
def report(product: str) -> None:
    """Create a scoped requirement and evidence report."""
    try:
        from .reporting import create_report
        typer.echo(str(create_report(root(), product)))
    except (SpecForgeError, OSError, RuntimeError) as exc:
        fail(exc)


@app.command()
def visualize(product: str) -> None:
    """Create a self-contained interactive specification graph."""
    try:
        from .visualization import create_visualization

        typer.echo(str(create_visualization(root(), product)))
    except (SpecForgeError, OSError, ValueError) as exc:
        fail(exc)


@app.command("sparql")
def sparql_command(
    product: str,
    query_file: Path = typer.Option(..., "--query", help="Local SPARQL SELECT/ASK query."),
) -> None:
    """Query the resolved RDF Dataset without requiring a graph database."""
    try:
        query = query_file.read_text(encoding="utf-8")
        result = Compiler(root()).semantic_dataset(product).query(query)
        if getattr(result, "type", None) == "ASK":
            typer.echo(json.dumps({"boolean": bool(result.askAnswer)}))
            return
        typer.echo(json.dumps([
            {str(name): (str(value) if value is not None else None) for name, value in row.asdict().items()}
            for row in result
        ], ensure_ascii=False, sort_keys=True, indent=2))
    except (SpecForgeError, OSError, ValueError) as exc:
        fail(exc)


@app.command("export-rif")
def export_rif_command(product: str, output: Path | None = typer.Option(None, "--output")) -> None:
    """Export the active positive Rule set as RIF Core XML."""
    try:
        from .datalog import compile_requirement_rules
        from .rif import export_rules

        _, _, _, rules, _, _ = Compiler(root()).load_inputs(product)
        rendered = export_rules(compile_requirement_rules(rules))
        if output:
            write_if_changed(output, rendered)
            typer.echo(str(output))
        else:
            typer.echo(rendered, nl=False)
    except (SpecForgeError, OSError, ValueError) as exc:
        fail(exc)


@app.command("rdf-check")
def rdf_check_command(source: Path) -> None:
    """Parse a local JSON-LD/Turtle/N-Quads/TriG input and validate its RDF contract."""
    try:
        from .semantic import SemanticDataset
        from .shacl import validate_dataset

        semantic = SemanticDataset.parse(source)
        result = validate_dataset(semantic)
        typer.echo(json.dumps({
            "conforms": result.conforms,
            "content_hash": semantic.content_hash(),
            "quads": sum(1 for _ in semantic.dataset.quads()),
        }, sort_keys=True))
        if not result.conforms:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (OSError, ValueError) as exc:
        fail(exc)


if __name__ == "__main__":
    app()
