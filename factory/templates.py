import re
import yaml
import logging
from dataclasses import dataclass
from pathlib import Path

from factory.errors import ValidationError

log = logging.getLogger(__name__)

_SKIP_FILES = {"template.yaml", "memory_schema.yaml"}


@dataclass
class Template:
    id: str
    root: Path
    meta: dict

    @classmethod
    def load(cls, template_id: str, *, templates_dir: Path) -> "Template":
        root = templates_dir / template_id
        if not root.is_dir():
            raise FileNotFoundError(f"Template '{template_id}' not found at {root}")
        meta_path = root / "template.yaml"
        if not meta_path.exists():
            raise FileNotFoundError(f"template.yaml missing from {root}")
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        log.debug("Loaded template '%s' v%s", template_id, meta.get("version"))
        return cls(id=template_id, root=root, meta=meta)

    def validate_inputs(self, inputs: dict) -> dict:
        """Validate user inputs against template spec; return dict with defaults applied.

        Raises ValidationError on first invalid field.
        """
        specs: dict = self.meta.get("inputs", {})
        defaults: dict = self.meta.get("defaults", {})

        # Start with template defaults, overlay user inputs
        result: dict = {}
        result.update(defaults)
        result.update(inputs)

        for field_name, spec in specs.items():
            value = result.get(field_name)

            if spec.get("required") and value is None:
                raise ValidationError(field_name, "is required")

            if value is None:
                default = spec.get("default")
                if default is not None:
                    result[field_name] = default
                continue

            field_type = spec.get("type")

            if field_type == "string":
                if not isinstance(value, str):
                    raise ValidationError(field_name, f"must be a string, got {type(value).__name__}")
                pattern = spec.get("pattern")
                if pattern and not re.fullmatch(pattern, value):
                    raise ValidationError(field_name, f"must match pattern '{pattern}' (got '{value}')")

            elif field_type == "enum":
                allowed = spec.get("values", [])
                if value not in allowed:
                    raise ValidationError(field_name, f"must be one of {allowed}, got '{value}'")

            elif field_type == "number":
                if not isinstance(value, (int, float)):
                    raise ValidationError(field_name, f"must be a number, got {type(value).__name__}")
                min_val = spec.get("min")
                if min_val is not None and value < min_val:
                    raise ValidationError(field_name, f"must be >= {min_val}, got {value}")
                max_val = spec.get("max")
                if max_val is not None and value > max_val:
                    raise ValidationError(field_name, f"must be <= {max_val}, got {value}")

        return result

    def render(self, normalized_inputs: dict) -> dict[str, str]:
        """Replace {{key}} placeholders in all template files.

        Returns {filename: rendered_text} for every non-meta file.
        """
        result: dict[str, str] = {}
        for path in self.root.iterdir():
            if path.name in _SKIP_FILES or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for key, value in normalized_inputs.items():
                text = text.replace(f"{{{{{key}}}}}", str(value))
            result[path.name] = text
        return result
