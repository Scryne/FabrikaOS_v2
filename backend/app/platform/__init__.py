"""Platform (control-plane) yönetim API'si — S17 / ADR-0019.

Tenant düzleminden yapısal olarak ayrık: uçlar ``tenant_cozumle``'den GEÇMEZ
(tenant-rbac-conventions'taki belgeli istisna), kimlik ``platform_access`` token
tipiyle ``public.platform_yonetici``'den doğrulanır.
"""
