import json
import logging
from apps.saas_core.models.audit import AuditLog

# Initialize standard Python logger for system-level errors
logger = logging.getLogger(__name__)

class AuditService:
    """
    Forensic-Grade Centralized Audit Service.
    Never breaks business flow, handles IP spoofing, and limits metadata explosion.
    """
    
    @staticmethod
    def log(request, workspace, action, resource_type, resource_id=None, metadata=None, status='SUCCESS', actor=None):
        try:
            if not workspace:
                return None
                
            ip = None
            user_agent = ''
            final_actor = actor

            # 1. Safe Request & IP Extraction (Prevents AttributeError if request is None)
            if request:
                ip = request.META.get('HTTP_CF_CONNECTING_IP') or \
                     request.META.get('HTTP_X_REAL_IP') or \
                     request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                     request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:1000]
                
                # If actor wasn't explicitly passed, try to get it from request
                if not final_actor and hasattr(request, 'user') and request.user.is_authenticated:
                    final_actor = request.user

            # 2. Metadata Sanitization & Explosion Prevention (Max ~10KB)
            safe_metadata = metadata or {}
            safe_metadata['status'] = status
            
            # Simple safeguard: If metadata is insanely huge, truncate it
            if len(json.dumps(safe_metadata)) > 10000:
                safe_metadata = {
                    "error": "Metadata truncated due to excessive size.",
                    "status": status,
                    "action": action
                }

            # 3. Fire & Forget Audit Creation
            return AuditLog.objects.create(
                workspace=workspace,
                actor=final_actor,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else "N/A",
                ip_address=ip.strip() if ip else None,
                user_agent=user_agent,
                metadata=safe_metadata
            )
            
        except Exception as e:
            # SILENT FAIL: If DB locks or Audit fails, it MUST NOT stop the user's action
            logger.exception(f"CRITICAL: AuditLog creation failed for action {action}: {str(e)}")
            return None