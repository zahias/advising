# email_templates.py
"""
Email template management for advising recommendations.
"""

from typing import Dict, List

# Email template configurations
EMAIL_TEMPLATES = {
    "default": {
        "name": "Standard Advising",
        "description": "Standard advising recommendations with course details",
        "note_prefix": "",
        "include_summary": True,
    },
    "probation": {
        "name": "Academic Probation",
        "description": "For students on academic probation - emphasizes recovery plan",
        "note_prefix": "Your current standing requires immediate attention. The following courses are essential to improve your academic progress:\n\n",
        "include_summary": True,
    },
    "excellent": {
        "name": "Excellent Standing",
        "description": "For high-performing students - includes optional advanced courses",
        "note_prefix": "Congratulations on your excellent academic standing! Here are your recommended courses plus some optional advanced electives:\n\n",
        "include_summary": True,
    },
    "near_graduation": {
        "name": "Near Graduation",
        "description": "For students close to completing degree",
        "note_prefix": "You are nearing graduation! The following courses will complete your degree requirements:\n\n",
        "include_summary": True,
    },
    "course_repeat": {
        "name": "Course Repeat Plan",
        "description": "For students retaking courses to improve GPA",
        "note_prefix": "Your advising plan includes course repeats to improve your GPA. Please review the repeat courses section below:\n\n",
        "include_summary": True,
    },
}


def get_template(template_name: str = "default") -> Dict:
    """Get email template configuration by name."""
    return EMAIL_TEMPLATES.get(template_name, EMAIL_TEMPLATES["default"])


def list_templates() -> List[str]:
    """List all available template names."""
    return list(EMAIL_TEMPLATES.keys())


def get_template_display_names() -> Dict[str, str]:
    """Get mapping of template keys to display names."""
    return {key: template["name"] for key, template in EMAIL_TEMPLATES.items()}


def get_template_descriptions() -> Dict[str, str]:
    """Get mapping of template keys to descriptions."""
    return {key: template["description"] for key, template in EMAIL_TEMPLATES.items()}


def add_template_note_prefix(template_name: str, note: str) -> str:
    """Add template-specific prefix to advisor note."""
    template = get_template(template_name)
    prefix = template.get("note_prefix", "")
    
    if prefix and note:
        return prefix + note
    elif prefix:
        return prefix.rstrip()
    else:
        return note
