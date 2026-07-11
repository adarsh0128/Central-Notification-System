from typing import Any
from jinja2 import Environment, meta

class TemplateValidationError(ValueError):
    """Exception raised when template validation fails due to missing variables."""
    pass

class TemplateService:
    def __init__(self) -> None:
        self.env = Environment()

    def get_required_variables(self, template_content: str) -> set[str]:
        """Extracts all placeholder variables from the template using Jinja2 AST."""
        try:
            ast = self.env.parse(template_content)
            return meta.find_undeclared_variables(ast)
        except Exception as e:
            raise TemplateValidationError(f"Invalid template format: {str(e)}")

    def render(self, template_content: str, variables: dict[str, Any]) -> str:
        """Renders the template content with the provided variables.
        
        Raises TemplateValidationError if any required variables are missing.
        """
        required = self.get_required_variables(template_content)
        missing = required - set(variables.keys())
        if missing:
            raise TemplateValidationError(
                f"Missing required template variables: {', '.join(sorted(missing))}"
            )

        try:
            template = self.env.from_string(template_content)
            return template.render(variables)
        except Exception as e:
            raise TemplateValidationError(f"Failed to render template: {str(e)}")

    def render_subject_and_body(
        self, template_content: str, subject_content: str | None, variables: dict[str, Any]
    ) -> tuple[str | None, str]:
        """Renders both the body content and optional subject line.
        
        Throws TemplateValidationError if validation fails on either.
        """
        # Validate body
        body = self.render(template_content, variables)
        
        # Validate and render subject if present
        subject = None
        if subject_content:
            subject = self.render(subject_content, variables)
            
        return subject, body
