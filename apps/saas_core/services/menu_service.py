from apps.saas_core.models.menu import Menu, RoleMenuPermission
from apps.saas_core.models.tenant import WorkspaceMember

class MenuService:
    """
    Generates dynamic sidebar menus based on Role, Permissions, and Subscription Features.
    """
    
    @staticmethod
    def get_sidebar_for_user(user, workspace_id):
        # 1. Get User's Role in the active workspace
        membership = WorkspaceMember.objects.filter(
            user=user, 
            workspace_id=workspace_id
        ).select_related('role').first()
        
        if not membership or not membership.role:
            return [] # Fallback for users without roles
        
        role = membership.role
        
        # 2. Get allowed menus from Layer 3 (Permissions)
        # MVP Logic: If the role is 'OWNER', show all active menus. 
        # Otherwise, strictly check RoleMenuPermission.
        if role.name == 'OWNER' or role.is_system_default:
            allowed_menus = Menu.objects.filter(is_active=True).order_by('sort_order')
        else:
            allowed_menu_ids = RoleMenuPermission.objects.filter(
                role=role, can_view=True
            ).values_list('menu_id', flat=True)
            allowed_menus = Menu.objects.filter(id__in=allowed_menu_ids, is_active=True).order_by('sort_order')

        # 3. Build the hierarchical Dictionary for dashboard.html
        menu_dict = {}
        for m in allowed_menus:
            menu_dict[m.id] = {
                'id': f"menu_{m.code}",
                'title': m.name,
                'icon': m.icon,
                'url': m.url,
                'type': 'flat', # Default to flat
                'parent_id': m.parent_id,
                'children': []
            }
        
        # 4. Organize into a Parent-Child Tree Structure
        sidebar = []
        for m in allowed_menus:
            if m.parent_id:
                # If it has a parent, append it to the parent's children list
                if m.parent_id in menu_dict:
                    menu_dict[m.parent_id]['children'].append(menu_dict[m.id])
                    menu_dict[m.parent_id]['type'] = 'dropdown' # Parent becomes a dropdown
            else:
                # If no parent, it's a top-level menu
                sidebar.append(menu_dict[m.id])
        
        return sidebar