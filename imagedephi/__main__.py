from imagedephi import main
from pathlib import Path
import yaml

import click

from . import redact_images, build_ruleset, show_redaction_plan


@click.group
def imagedephi():
    """Redact microscopy whole slide images."""
    pass


@imagedephi.command
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir", type=click.Path(exists=True, file_okay=False, writable=True, path_type=Path)
)
def run(input_dir: Path, output_dir: Path) -> None:
    """Run in CLI-only mode."""
    redact_images(input_dir, output_dir)
    click.echo("Done!")


@imagedephi.command
@click.argument("base-rules", type=click.File("r"))
@click.argument("rules-override", type=click.File('r'))
def print_rulesets(base_rules: click.File, rules_override: click.File) -> None:
    """Utility to print python representation of yaml rulesets."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, rules_override]
    ]
    click.echo([base_rule_set, override_rule_set])


@imagedephi.command
@click.argument("image", type=click.Path())
@click.argument("base-rules", type=click.File("r"))
@click.argument("override-rules", type=click.File("r"))
def redaction_plan(
    image: click.Path,
    base_rules: click.File,
    override_rules: click.File
) -> None:
    """Print the redaction plan for a given image and rules."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, override_rules]
    ]
    show_redaction_plan(image, base_rule_set, override_rule_set)


if __name__ == "__main__":
    main.imagedephi()
