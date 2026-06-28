from django.core.cache import cache
from apps.saas_core.models.tenant import WorkspaceMember

class PolicyEngine:
    """Centralized Authorization Engine with Redis Caching."""
    CACHE_TIMEOUT = 3600

    @staticmethod
    def _generate_cache_key(workspace_id, user_id):
        return f"ws:{workspace_id}:user:{user_id}:perms"

    @staticmethod
    def get_user_permissions(user, workspace):
        if not user or not workspace:
            return set()
            
        cache_key = PolicyEngine._generate_cache_key(workspace.id, user.id)
        cached_perms = cache.get(cache_key)
        
        if cached_perms is not None:
            return cached_perms

        member = WorkspaceMember.objects.filter(
            workspace=workspace, user=user, is_deleted=False
        ).select_related('role').first()
        
        perms = set()
        if member and member.role:
            # 🟢 FIX: Give absolute power to OWNER or System Default roles
            if member.role.is_system_default or member.role.name == 'OWNER':
                perms = {'ALL_ACCESS'}
            else:
                perms = set(member.role.permissions_m2m.values_list('code', flat=True))

        cache.set(cache_key, perms, PolicyEngine.CACHE_TIMEOUT)
        return perms

    @staticmethod
    def can(user, workspace, action_code):
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
            
        user_perms = PolicyEngine.get_user_permissions(user, workspace)
        # 🟢 FIX: Check if they have specific permission OR 'ALL_ACCESS'
        return 'ALL_ACCESS' in user_perms or action_code in user_perms

    @staticmethod
    def invalidate_cache(workspace_id, user_id=None):
        if user_id:
            cache.delete(PolicyEngine._generate_cache_key(workspace_id, user_id))