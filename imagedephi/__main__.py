from imagedephi import main
from pathlib import Path

import click
import yaml

from . import build_ruleset, redact_images, redact_images_using_rules, show_redaction_plan


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
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument("base-rules", type=click.File("r"))
@click.argument("override-rules", type=click.File("r"))
def run_rules(
    input_dir: Path, output_dir: Path, base_rules: click.File, override_rules: click.File
):
    """Redact images in a folder according to given rule sets."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, override_rules]
    ]
    redact_images_using_rules(input_dir, output_dir, base_rule_set, override_rule_set)


@imagedephi.command
@click.argument("image", type=click.Path())
@click.argument("base-rules", type=click.File("r"))
@click.argument("override-rules", type=click.File("r"))
def redaction_plan(image: click.Path, base_rules: click.File, override_rules: click.File) -> None:
    """Print the redaction plan for a given image and rules."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, override_rules]
    ]
    show_redaction_plan(image, base_rule_set, override_rule_set)


if __name__ == "__main__":
    main.imagedephi()
