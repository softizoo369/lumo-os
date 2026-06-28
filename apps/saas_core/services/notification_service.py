from django.utils import timezone
from apps.saas_core.models.notification import Notification

class NotificationService:
    """
    Centralized Broadcaster for System Notifications.
    """
    @staticmethod
    def send(recipient, title, message, workspace=None, notif_type='INFO', action_url=None):
        """Sends a single notification to a user."""
        if not recipient:
            return None
            
        return Notification.objects.create(
            workspace=workspace,
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notif_type,
            action_url=action_url
        )

    @staticmethod
    def mark_as_read(notification_id, user):
        """Marks a specific notification as read."""
        Notification.objects.filter(id=notification_id, recipient=user).update(
            is_read=True, 
            read_at=timezone.now()
        )
        
    @staticmethod
    def mark_all_as_read(user):
        """Marks all unread notifications as read for a user."""
        Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True, 
            read_at=timezone.now()
        )