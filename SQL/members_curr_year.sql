WITH base_data AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewals.value AS renewal_type,
        addresses.value AS home_address,
        home_phones.value AS home_phone,
        cell_phones.value AS cell_phone,
        primary_names.value AS primary_name,
        primary_emails.value AS primary_email,
        secondary_names.value AS secondary_name,
        emergency_contacts.value AS emergency_contact,
        emergency_phones.value AS emergency_phone,
        child_photos.value AS child_photo,
        child_1_names.value AS child_1_name,
        child_2_names.value AS child_2_name,
        child_3_names.value AS child_3_name,
        child_4_names.value AS child_4_name,
        child_5_names.value AS child_5_name,
        customizations
    FROM syc_orders
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Confirm Membership Type'
    ) renewals ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Primary Address' OR elem->>'label' = 'Address'
    ) addresses ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Home Phone'
    ) home_phones ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Cell Phone'
    ) cell_phones ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Primary Member Name'
    ) primary_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Primary Email'
    ) primary_emails ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Secondary Member Name'
    ) secondary_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Emergency Contact Name'
    ) emergency_contacts ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Emergency Contact Phone'
    ) emergency_phones ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'SYC Photography'
    ) child_photos ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Child Family Member #1'
    ) child_1_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Child Family Member #2'
    ) child_2_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Child Family Member #3'
    ) child_3_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Child Family Member #4'
    ) child_4_names ON true
    LEFT JOIN LATERAL (
        SELECT value->>'value' AS value
        FROM jsonb_array_elements(customizations) elem
        WHERE elem->>'label' = 'Child Family Member #5'
    ) child_5_names ON true
    WHERE product_name ILIKE '%Membership%'
    AND EXTRACT(YEAR FROM created_on) = EXTRACT(YEAR FROM CURRENT_DATE)
),
primary_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        primary_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Primary Member' AS relationship,
        primary_name
    FROM base_data
    WHERE primary_name IS NOT NULL AND primary_name <> '' AND LOWER(primary_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
secondary_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        secondary_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Secondary Member' AS relationship,
        primary_name
    FROM base_data
    WHERE secondary_name IS NOT NULL AND secondary_name <> '' AND LOWER(secondary_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
child_1_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        child_1_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Child Member' AS relationship,
        primary_name
    FROM base_data
    WHERE child_1_name IS NOT NULL AND child_1_name <> '' AND LOWER(child_1_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
child_2_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        child_2_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Child Member' AS relationship,
        primary_name
    FROM base_data
    WHERE child_2_name IS NOT NULL AND child_2_name <> '' AND LOWER(child_2_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
child_3_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        child_3_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Child Member' AS relationship,
        primary_name
    FROM base_data
    WHERE child_3_name IS NOT NULL AND child_3_name <> '' AND LOWER(child_3_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
child_4_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        child_4_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Child Member' AS relationship,
        primary_name
    FROM base_data
    WHERE child_4_name IS NOT NULL AND child_4_name <> '' AND LOWER(child_4_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
),
child_5_members AS (
    SELECT
        id,
        order_number,
        created_on,
        product_name,
        renewal_type,
        home_address,
        home_phone,
        cell_phone,
        child_5_name AS member_name,
        primary_email,
        emergency_contact,
        emergency_phone,
        child_photo,
        customizations,
        'Child Member' AS relationship,
        primary_name
    FROM base_data
    WHERE child_5_name IS NOT NULL AND child_5_name <> '' AND LOWER(child_5_name) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
)
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM primary_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM secondary_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM child_1_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM child_2_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM child_3_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM child_4_members
UNION ALL
SELECT 
    id,
    order_number,
    created_on,
    product_name,
    renewal_type,
    home_address,
    home_phone,
    cell_phone,
    member_name,
    primary_email,
    emergency_contact,
    emergency_phone,
    child_photo,
    customizations,
    relationship,
    primary_name
FROM child_5_members;
