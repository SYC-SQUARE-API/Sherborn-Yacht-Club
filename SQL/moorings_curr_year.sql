SELECT
    syc_orders.product_name AS location,
    primary_names.value AS primary_name,
    primary_emails.value AS primary_email,
    types_of_boat.value AS type_of_boat,
    colors.value AS color,
    letters.value AS letter,
    COALESCE(CASE 
        WHEN syc_orders.product_name ILIKE '%Shoreline%' THEN 'Shoreline'
        ELSE rows.value
    END, 'Shoreline') AS row,
    town_boat_permits.value AS town_boat_permit,
    identify_boat.value AS identify_boat,
    addresses.value AS address,
    phones.value AS phone,
    CASE 
        WHEN EXISTS (
            SELECT 1
            FROM syc_orders sub_orders
            WHERE sub_orders.order_number = syc_orders.order_number
            AND sub_orders.product_name ILIKE '%Mooring Services%'
        ) THEN 'Yes'
        ELSE 'No'
    END AS mooring_services
FROM syc_orders
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Name'
) primary_names ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Email'
) primary_emails ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Type of Boat'
) types_of_boat ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Boat Color'
) colors ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Location'
) locations ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(variant_options) elem
    WHERE elem->>'optionName' = 'Letter'
) letters ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(variant_options) elem
    WHERE elem->>'optionName' = 'Row'
) rows ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Town Boat Permit #'
) town_boat_permits ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Identifying features of the boat'
) identify_boat ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Address'
) addresses ON true
LEFT JOIN LATERAL (
    SELECT value->>'value' AS value
    FROM jsonb_array_elements(customizations) elem
    WHERE elem->>'label' = 'Phone'
) phones ON true
WHERE syc_orders.product_name ILIKE '%Moorings%'
AND EXTRACT(YEAR FROM syc_orders.created_on) = EXTRACT(YEAR FROM CURRENT_DATE)
AND primary_names.value IS NOT NULL
AND primary_names.value <> '';
