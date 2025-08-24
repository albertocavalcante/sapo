"""Templates module for generating config files.

This module provides functionality for rendering templates for various configuration files.
"""

from pathlib import Path
from typing import Union, Optional, Any

from jinja2 import Environment, FileSystemLoader


def render_template_from_file(
    template_path: Union[str, Path],
    template_name: str,
    context: dict[str, Any],
    output_path: Optional[Path] = None,
) -> str:
    """Render a template from a file.

    Args:
        template_path: Path to the template file or module name
        template_name: Name of the template file
        context: Context variables for the template
        output_path: Optional path to write the rendered template

    Returns:
        str: The rendered template
    """
    # If template_path is a string, it's a module name
    if isinstance(template_path, str):
        # Get the path to the template
        module_path = Path(__file__).parent / template_path
        if not module_path.exists():
            raise ValueError(f"Template module path not found: {module_path}")
    else:
        module_path = template_path

    # Create Jinja environment
    # Autoescape would break Docker Compose and shell script generation
    env = Environment(  # nosec B701
        loader=FileSystemLoader(module_path),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Get the template
    template = env.get_template(template_name)
    rendered = template.render(**context)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(rendered)

    return rendered


__all__ = ["render_template_from_file"]
