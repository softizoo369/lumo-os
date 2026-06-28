from apps.saas_core.models.company import Company, CompanyAccess
from apps.saas_core.models.tenant import WorkspaceMember

class CompanyAccessService:
    
    @staticmethod
    def grant_access(member: WorkspaceMember, company: Company, is_primary: bool = False):
        """Grants a member access to a specific company."""
        access, created = CompanyAccess.objects.get_or_create(
            workspace_id=member.workspace_id,
            member=member,
            company=company,
            defaults={'is_primary': is_primary}
        )
        if not created and is_primary:
            access.is_primary = True
            access.save()
        return access

    @staticmethod
    def revoke_access(member: WorkspaceMember, company: Company):
        """Revokes a member's access from a specific company."""
        CompanyAccess.objects.filter(member=member, company=company).update(is_deleted=True)

    @staticmethod
    def get_accessible_companies(member: WorkspaceMember):
        """Returns a queryset of companies the user is allowed to access."""
        # System OWNERs usually get bypass access to all companies
        if member.role and member.role.is_system_default and member.role.name == 'OWNER':
            return Company.objects.filter(workspace_id=member.workspace_id, is_deleted=False)
            
        # Regular users get explicitly assigned companies
        accessed_company_ids = CompanyAccess.objects.filter(
            member=member, 
            is_deleted=False
        ).values_list('company_id', flat=True)
        
        return Company.objects.filter(id__in=accessed_company_ids, is_deleted=False)