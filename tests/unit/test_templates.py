import pytest
from app.services.template import TemplateService, TemplateValidationError

def test_template_rendering_success() -> None:
    service = TemplateService()
    template = "Hello {{name}}, your OTP is {{code}}."
    variables = {"name": "Bob", "code": "123456"}
    
    result = service.render(template, variables)
    assert result == "Hello Bob, your OTP is 123456."

def test_template_rendering_missing_variables() -> None:
    service = TemplateService()
    template = "Hello {{name}}, your OTP is {{code}}."
    variables = {"name": "Bob"}  # missing 'code'
    
    with pytest.raises(TemplateValidationError) as exc_info:
        service.render(template, variables)
        
    assert "Missing required template variables: code" in str(exc_info.value)

def test_template_rendering_subject_and_body() -> None:
    service = TemplateService()
    body_template = "Body: {{body_var}}"
    subject_template = "Subject: {{subj_var}}"
    variables = {"body_var": "Content", "subj_var": "Alert"}
    
    subj, body = service.render_subject_and_body(body_template, subject_template, variables)
    assert subj == "Subject: Alert"
    assert body == "Body: Content"

def test_template_rendering_extra_variables_ignored() -> None:
    service = TemplateService()
    template = "Hi {{name}}"
    variables = {"name": "Bob", "extra_var": "Ignored"}
    
    result = service.render(template, variables)
    assert result == "Hi Bob"
