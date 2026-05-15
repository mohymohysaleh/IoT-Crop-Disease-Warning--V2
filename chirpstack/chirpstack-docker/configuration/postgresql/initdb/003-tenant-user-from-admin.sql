-- ChirpStack v4: tenants with no tenant_user rows are invisible for normal admin sessions.
-- Idempotent after fresh init: skips tenants that already have at least one linked user.
INSERT INTO public.tenant_user (tenant_id, user_id, created_at, updated_at, is_admin, is_device_admin, is_gateway_admin)
SELECT t.id, u.id, NOW(), NOW(), true, true, true
FROM public.tenant t
CROSS JOIN LATERAL (
    SELECT id
    FROM public."user"
    WHERE is_admin IS TRUE AND is_active IS TRUE
    ORDER BY created_at ASC
    LIMIT 1
) u
WHERE NOT EXISTS (
    SELECT 1 FROM public.tenant_user tu WHERE tu.tenant_id = t.id
);
