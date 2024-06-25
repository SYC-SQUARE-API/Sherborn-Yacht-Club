SELECT
  o.createdOn,
  o.customerEmail AS primaryEmail,
  li.productName AS productName,
  cust.label AS relation,
  cust.value AS memberName,
  addressCust.value AS address,
  sycPhotographyCust.value AS sycPhotography,
  homePhoneCust.value AS homePhone,
  cellPhoneCust.value AS cellPhone,
  emergencyContactNameCust.value AS emergencyContactName,
  emergencyContactPhoneCust.value AS emergencyContactPhone,
  CASE
    WHEN cust.label IN ('Child Family Member #1', 'Child Family Member #2', 'Child Family Member #3', 'Child Family Member #4') THEN
      (SELECT custom.value
       FROM UNNEST(li.customizations) custom WITH OFFSET pos
       WHERE pos = (SELECT pos FROM UNNEST(li.customizations) custom2 WITH OFFSET pos WHERE custom2.label = cust.label AND custom2 = cust) + 1
      )
    ELSE NULL
  END AS dateOfBirth,
  confirmMembershipTypeCust.value AS confirmMembershipType,
  CASE
    WHEN cust.label NOT IN ('Primary Member Name', 'Primary Membership Name') THEN
      (SELECT primaryMember.value
       FROM UNNEST(li.customizations) primaryMember
       WHERE primaryMember.label IN ('Primary Member Name', 'Primary Membership Name'))
    ELSE NULL
  END AS primaryMemberName
FROM
  SYC.ORDERS AS o,
  UNNEST(o.lineItems) AS li,
  UNNEST(li.customizations) AS cust
LEFT JOIN UNNEST(li.customizations) AS addressCust
  ON addressCust.label IN ('Address', 'Primary Address')
LEFT JOIN UNNEST(li.customizations) AS sycPhotographyCust
  ON sycPhotographyCust.label = 'SYC Photography'
LEFT JOIN UNNEST(li.customizations) AS homePhoneCust
  ON homePhoneCust.label = 'Home Phone'
LEFT JOIN UNNEST(li.customizations) AS cellPhoneCust
  ON cellPhoneCust.label = 'Cell Phone'
LEFT JOIN UNNEST(li.customizations) AS emergencyContactNameCust
  ON emergencyContactNameCust.label = 'Emergency Contact Name'
LEFT JOIN UNNEST(li.customizations) AS emergencyContactPhoneCust
  ON emergencyContactPhoneCust.label = 'Emergency Contact Phone'
LEFT JOIN UNNEST(li.customizations) AS confirmMembershipTypeCust
  ON confirmMembershipTypeCust.label = 'Confirm Membership Type'
WHERE
  li.productName LIKE '%Member%'
  AND EXTRACT(YEAR FROM o.createdOn) = 2023
  AND (
    cust.label IN (
      'Primary Member Name',
      'Primary Membership Name',
      'Secondary Member Name',
      'Child Family Member #1',
      'Child Family Member #2',
      'Child Family Member #3',
      'Child Family Member #4'
    )
    AND cust.value IS NOT NULL
    AND cust.value <> ''
  )
  AND LOWER(cust.value) LIKE {{'%' + textInput1.value.trim().toLowerCase() + '%'}}
GROUP BY
  o.createdOn,
  primaryEmail,
  productName,
  memberName,
  cust.label,
  address,
  sycPhotography,
  homePhone,
  cellPhone,
  emergencyContactName,
  emergencyContactPhone,
  dateOfBirth,
  confirmMembershipType,
  primaryMemberName