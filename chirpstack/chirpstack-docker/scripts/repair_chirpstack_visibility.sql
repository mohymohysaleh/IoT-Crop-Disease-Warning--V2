-- Fix broken ChirpStack DBs where tenant rows were deleted but applications/gateways still
-- reference their UUIDs (UI shows no tenants / nothing under Network Server).
-- Safe to run multiple times.

-- 1) Recreate missing tenant rows from FK-like references
INSERT INTO public.tenant (
    id,
    created_at,
    updated_at,
    name,
    description,
    can_have_gateways,
    max_device_count,
    max_gateway_count,
    private_gateways_up,
    private_gateways_down,
    tags
)
SELECT DISTINCT
    x.tenant_id,
    NOW(),
    NOW(),
    'ChirpStack',
    '',
    true,
    0,
    0,
    false,
    false,
    '{}'::jsonb
FROM (
    SELECT tenant_id FROM public.application
    UNION
    SELECT tenant_id FROM public.gateway
) AS x
WHERE NOT EXISTS (SELECT 1 FROM public.tenant t WHERE t.id = x.tenant_id);

-- 2) Link first global admin to every tenant that has no tenant_user row yet
INSERT INTO public.tenant_user (
    tenant_id,
    user_id,
    created_at,
    updated_at,
    is_admin,
    is_device_admin,
    is_gateway_admin
)
SELECT t.id, u.id, NOW(), NOW(), true, true, true
FROM public.tenant t
CROSS JOIN LATERAL (
    SELECT id
    FROM public."user"
    WHERE is_admin IS TRUE AND is_active IS TRUE
    ORDER BY created_at ASC
    LIMIT 1
) u
WHERE NOT EXISTS (SELECT 1 FROM public.tenant_user tu WHERE tu.tenant_id = t.id);
