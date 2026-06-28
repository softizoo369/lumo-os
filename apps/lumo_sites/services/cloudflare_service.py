import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class CloudflareService:
    """
    Enterprise Cloudflare API Integration for SaaS Custom Domains.
    Handles automated SSL provisioning and CNAME/TXT routing.
    """
    
    @staticmethod
    def get_headers():
        return {
            "Authorization": f"Bearer {settings.CF_API_TOKEN}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def get_base_url():
        return f"https://api.cloudflare.com/client/v4/zones/{settings.CF_ZONE_ID}/custom_hostnames"

    @staticmethod
    def add_custom_hostname(domain_name):
        """
        Cloudflare-এ ক্লায়েন্টের ডোমেইন অ্যাড করে এবং SSL ভেরিফিকেশনের জন্য TXT/CNAME রেকর্ড জেনারেট করে।
        """
        print("DEBUG - CF_ZONE_ID:", settings.CF_ZONE_ID)
        print("DEBUG - CF_API_TOKEN:", settings.CF_API_TOKEN)
        payload = {
            "hostname": domain_name,
            "ssl": {
                "method": "txt",  # TXT রেকর্ডের মাধ্যমে SSL ভেরিফাই হবে
                "type": "dv",     # Domain Validated SSL
                "settings": {
                    "min_tls_version": "1.2"
                }
            }
        }

        try:
            response = requests.post(
                CloudflareService.get_base_url(),
                headers=CloudflareService.get_headers(),
                json=payload,
                timeout=10
            )
            response_data = response.json()

            if response.status_code == 201 and response_data.get("success"):
                result = response_data["result"]
                # ক্লাউডফ্লেয়ারের জেনারেট করা ডেটা রিটার্ন করছি
                return {
                    "success": True,
                    "cloudflare_id": result.get("id"),
                    "ownership_verification": result.get("ownership_verification", {}),
                    "ssl_validation": result.get("ssl", {}).get("validation_records", [])
                }
            else:
                logger.error(f"Cloudflare Error: {response_data.get('errors')}")
                return {"success": False, "error": response_data.get('errors', [{'message': 'Unknown error'}])[0]['message']}
                
        except Exception as e:
            logger.error(f"Cloudflare Exception: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_custom_hostname(cloudflare_id):
        """
        ক্লায়েন্ট যখন ডোমেইন ডিলিট করবে, তখন Cloudflare থেকেও সেটি রিমুভ করে দেবে।
        """
        if not cloudflare_id:
            return {"success": True} 
            
        try:
            url = f"{CloudflareService.get_base_url()}/{cloudflare_id}"
            response = requests.delete(url, headers=CloudflareService.get_headers(), timeout=10)
            
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": "Failed to delete from Cloudflare"}
            
        except Exception as e:
            logger.error(f"Cloudflare Delete Exception: {str(e)}")
            return {"success": False, "error": str(e)}