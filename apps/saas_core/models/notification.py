from django.db import models
from django.conf import settings
from apps.saas_core.models.base import LumoBaseModel

class Notification(LumoBaseModel):
    """
    Enterprise In-App Notification Model.
    Stores alerts, system updates, and user mentions.
    """
    NOTIFICATION_TYPES = (
        ('INFO', 'Information'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('SYSTEM', 'System Alert'),
    )

    workspace = models.ForeignKey('saas_core.Workspace', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='INFO')
    
    # Optional URL to redirect the user when they click the notification
    action_url = models.CharField(max_length=500, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_notification'
        ordering = ['-created_at']
        indexes = [
            # 🟢 High-performance index for fetching unread notifications quickly
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.recipient.email} - {self.title}"