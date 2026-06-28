# apps/saas_core/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_image_size(value):
    """Validator to strictly enforce a 1MB max file size on the server."""
    limit_mb = 1
    limit_bytes = limit_mb * 1024 * 1024
    if value.size > limit_bytes:
        raise ValidationError(
            _('File size cannot exceed %(limit)s MB. Current size is %(actual)s MB.'),
            params={
                'limit': limit_mb, 
                'actual': round(value.size / (1024 * 1024), 2)
            }
        )