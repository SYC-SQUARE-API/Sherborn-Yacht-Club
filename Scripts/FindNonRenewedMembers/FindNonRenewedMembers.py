#!/usr/bin/env python3

import os
import sys
import gspread
from gspread.exceptions import *
import requests
from requests.auth import HTTPBasicAuth
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
from dateutil import parser as parsedate

filter_type_members = [
                        'Family Membership',
                        'Partner Membership',
                        'Individual Membership',
                        'Emeritus Membership',
                        'Junior Membership',
                    ]

spreadsheet_header_members = [
                        'Order No',
                        'Primary Name',
                        'Primary Email',
                        'Secondary Name',
                        'Secondary Email',
                        'Membership Type',
                        'Renewal Type',
                        'Home Address',
                        'Home Phone',
                        'Cell Phone',
                        'Emergency Contact',
                        'Emergency Phone',
                        'Child #1 Name',
                        'Child #1 DOB',
                        'Child #2 Name',
                        'Child #2 DOB',
                        'Child #3 Name',
                        'Child #3 DOB',
                        'Child #4 Name',
                        'Child #4 DOB',
                        'Child #5 Name',
                        'Child #5 DOB',
                    ]

admin_email_accts = [
                        'commodore@sherbornyachtclub.org',
                        'info@sherbornyachtclub.org',
                        'instruction@sherbornyachtclub.org',
                        'brent.holden@gmail.com',
                        'kenfrankel@gmail.com',
                    ]

## function to get a nested list of all orders from squarespace
## returns: dictionary of orders from json result
def get_squarespace_items(api_endpoint, json_return, parameters):
    item_list = []
    commerce_creds = os.environ.get('SQUARESPACE_API_KEY')

    # define JSON headers, API key pulled from environment variable SQUARESPACE_API_KEY
    headers = {
        "Authorization": "Bearer " + commerce_creds,
        "User-Agent": "MembershipBot"
    }

    response = requests.get(api_endpoint, headers=headers, params=parameters)
    if response.raise_for_status():
        pass
    else:
        json_data = response.json()

    if response.status_code == requests.codes.ok:
        for item in json_data[json_return]:
            item_list.append(item)

        if json_data['pagination']['hasNextPage']:
            return (item_list + get_squarespace_items(json_data['pagination']['nextPageUrl'], json_return, None))
    else:
        print("Return status was NOT OK: %s" % response.status_code)
        return False

    return item_list

def parse_squarespace_orders(unparsed_orders, filter_types):

    parsed_orderlist = []

    # iterate through every lineItem, which corresponds to an order in the system
    # we further select by only finding orders which correspond to memberships
    for member in unparsed_orders:
        parsed_order = {
                            'order_no': '',
                            'name': '',
                            'email': '',
                            'secondary_name': '',
                            'secondary_email': '',
                            'membership_type': '',
                            'renewal': '',
                            'price_paid': '',
                            'price_discount': '',
                            'home_address': '',
                            'home_phone': '',
                            'cell_phone': '',
                            'emergency_contact_name': '',
                            'emergency_contact_phone': '',
                            'child_member_1_name': '',
                            'child_member_1_dob': '',
                            'child_member_2_name': '',
                            'child_member_2_dob': '',
                            'child_member_3_name': '',
                            'child_member_3_dob': '',
                            'child_member_4_name': '',
                            'child_member_4_dob': '',
                            'child_member_5_name': '',
                            'child_member_5_dob': '',
                            'mooring_location': '',
                            'mooring_color': '',
                            'boat_type': '',
                            'boat_color': '',
                            'town_permit_no': '',
                            'mooring_svcs': 'No',
                            'year': '',
                        }

        add_member_to_list = False

        parsed_order['order_no'] = member['orderNumber']
        parsed_order['name'] = member['billingAddress']['firstName'] + " " + member['billingAddress']['lastName']
        parsed_order['email'] = member['customerEmail']

        # Figure out the home address
        try:
            street_address = member['billingAddress']['address1'] + " " + member['billingAddress']['address2']
        except TypeError:
            street_address = member['billingAddress']['address1']

        parsed_order['home_address'] = street_address + ", " + member['billingAddress']['city'] + ", " + member['billingAddress']['state'] + " " + member['billingAddress']['postalCode']

        parsed_order['year'] = parsedate.isoparse(member['modifiedOn']).year
        parsed_order['fulfillment'] = member['fulfillmentStatus']
        parsed_order['price_paid'] = member['grandTotal']['value']
        parsed_order['price_discount'] = member['discountTotal']['value']

        for line_item in member['lineItems']:
            # Check if they bought a membership
            # Year may be updated, check to see if suffix matches a member filter type
            if line_item['productName'].endswith(tuple(filter_type_members)):
                parsed_order['membership_type'] = line_item['productName']

                if line_item['customizations']:
                    for index, customization in enumerate(line_item['customizations']):
                        for item in customization:
                            if customization['label'] == 'Confirm Membership Type':
                                parsed_order['renewal'] = customization['value']
                            elif customization['label'] == 'Home Phone':
                                parsed_order['home_phone'] = customization['value'].strip()
                            elif customization['label'] == 'Cell Phone':
                                parsed_order['cell_phone'] = customization['value'].strip()
                            elif customization['label'] == 'Primary Address':
                                parsed_order['home_address'] = customization['value']
                            elif customization['label'] == 'Secondary Member Name':
                                parsed_order['secondary_name'] = customization['value']
                            elif customization['label'] == 'Secondary Member Email':
                                parsed_order['secondary_email'] = customization['value']
                            elif customization['label'] == 'Emergency Contact Name':
                                parsed_order['emergency_contact_name'] = customization['value']
                            elif customization['label'] == 'Emergency Contact Phone':
                                parsed_order['emergency_contact_phone'] = customization['value'].strip()
                            elif (customization['label'] == 'Child Family Member #1'):
                                parsed_order['child_member_1_name'] = line_item['customizations'][index][item]
                                parsed_order['child_member_1_dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #2'):
                                parsed_order['child_member_2_name'] = line_item['customizations'][index][item]
                                parsed_order['child_member_2_dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #3'):
                                parsed_order['child_member_3_name'] = line_item['customizations'][index][item]
                                parsed_order['child_member_3_dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #4'):
                                parsed_order['child_member_4_name'] = line_item['customizations'][index][item]
                                parsed_order['child_member_4_dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #5'):
                                parsed_order['child_member_5_name'] = line_item['customizations'][index][item]
                                parsed_order['child_member_5_dob'] = line_item['customizations'][index+1][item]

            if line_item['productName'].endswith(tuple(filter_types)):
                add_member_to_list = True

        if add_member_to_list:
            parsed_orderlist.append(parsed_order)

    return parsed_orderlist

def get_spreadsheet(spreadsheet_title, addtl_share_perms=[], notify_users=False):

    # define the scope
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

    # add credentials to the account
    credentials = ServiceAccountCredentials.from_json_keyfile_name('googleCreds.json', scope)

    # authorize the clientsheet
    client = gspread.authorize(credentials)

    # get the instance of the Spreadsheet
    try:
        handler = client.open(spreadsheet_title)
    except SpreadsheetNotFound:
        handler = client.create(spreadsheet_title)

    print("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))

    email_perms = admin_email_accts + addtl_share_perms
    for email in email_perms:
        handler.share(email, perm_type='user', role='writer', notify=notify_users)

    return handler

def update_spreadsheet(spreadsheet, worksheet_title, header_row, rows_to_add):

    # make a spreadsheet for the year if necessary
    # set the target_sheet for the sheet we'll be writing to
    worksheets = spreadsheet.worksheets()

    target_sheet = None
    for sheet in worksheets:
        if sheet.title == worksheet_title:
            target_sheet = sheet

    # If sheet was not found create it
    if not target_sheet:
        target_sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1, cols=len(rows_to_add[0]))

    target_sheet.clear()
    target_sheet.resize(rows=1)
    target_sheet.append_row(header_row, value_input_option='USER-ENTERED', table_range='A1:B1')

    start_row = 1
    target_sheet.append_rows(rows_to_add, value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    target_sheet.columns_auto_resize(0, len(rows_to_add[0]))

    return True

def sync_memberships(orders_in_json, year):

    spreadsheet_title = "SYC Members"
    worksheet_title = "%s" % year
    spreadsheet_header = spreadsheet_header_members

    formatted_orders = []
    parsed_orders = parse_squarespace_orders(orders_in_json, filter_type_members)
    for order in parsed_orders:
        formatted_order = [
                            order['order_no'],
                            order['name'],
                            order['email'],
                            order['secondary_name'],
                            order['secondary_email'],
                            order['membership_type'],
                            order['renewal'],
                            order['home_address'],
                            order['home_phone'],
                            order['cell_phone'],
                            order['emergency_contact_name'],
                            order['emergency_contact_phone'],
                            order['child_member_1_name'],
                            order['child_member_1_dob'],
                            order['child_member_2_name'],
                            order['child_member_2_dob'],
                            order['child_member_3_name'],
                            order['child_member_3_dob'],
                            order['child_member_4_name'],
                            order['child_member_4_dob'],
                            order['child_member_5_name'],
                            order['child_member_5_dob'],
                            ]
        formatted_orders.append(formatted_order)

    if not formatted_orders:
        return 0

    # get the spreadsheet handler
    gs = get_spreadsheet(spreadsheet_title)

    # update the google sheet
    # check for column 1 for non-duplicate entries
    try:
        update_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_orders)
    except Exception as e:
        print("failure updating google sheets: %s" % e)
        return 1

    return 0

def main():
    # Added tests for environment variables
    if os.environ.get('SQUARESPACE_API_KEY') is None:
        print("Failed to pass SQUARESPACE_API_KEY")
        return 1

    orders_api_endpoint = "https://api.squarespace.com/1.0/commerce/orders"
    transactions_api_endpoint = "https://api.squarespace.com/1.0/commerce/transactions"

    all_members_before_2022 = []
    years = [2021, 2020]

    for year in years:
        year_beginning = date(year, 1, 1).isoformat()+ 'T00:00:00.0Z'
        year_end = date(year, 12, 30).isoformat()+ 'T00:00:00.0Z'

        request_parameters = {
            "modifiedAfter": year_beginning,
            "modifiedBefore": year_end,
        }

        try:
            json_var = 'result'
            orders_in_json = get_squarespace_items(orders_api_endpoint, json_var, request_parameters)

        except requests.exceptions.HTTPError as error:
            print("Failed to get new members: %s" % error)
            return 1

        sync_memberships(orders_in_json, year)

        for order in orders_in_json:
            all_members_before_2022.append(order)

    # Write out non-unique member set
    sync_memberships(all_members_before_2022, 'Prior 2022 All')

    # Now get all 2022 users
    all_members_in_2022 = []
    year = 2022
    year_beginning = date(year, 1, 1).isoformat()+ 'T00:00:00.0Z'
    year_end = date(year, 12, 30).isoformat()+ 'T00:00:00.0Z'

    request_parameters = {
        "modifiedAfter": year_beginning,
        "modifiedBefore": year_end,
    }

    try:
        json_var = 'result'
        all_members_in_2022 = get_squarespace_items(orders_api_endpoint, json_var, request_parameters)
    except requests.exceptions.HTTPError as error:
        print("Failed to get new members: %s" % error)
        return 1

    all_members_in_2022_emails = set()
    for current_member in all_members_in_2022:
        all_members_in_2022_emails.add(current_member['customerEmail'])

    all_members_prior_2022_emails = set()
    for prior_member in all_members_before_2022:
        all_members_prior_2022_emails.add(prior_member['customerEmail'])

    members_nonrenew_emails = list(all_members_prior_2022_emails - all_members_in_2022_emails)

    members_nonrenew = []
    # Reconstitute the members list
    for nonrenew_email in members_nonrenew_emails:
        for member in all_members_before_2022:
            if member['customerEmail'] == nonrenew_email:
                members_nonrenew.append(member)

    sync_memberships(members_nonrenew, 'Not Renewed')

    return 0

if __name__ == "__main__":
    return_val = 1
    try:
        return_val = main()
    except KeyboardInterrupt:
        print("Caught a control-C. Bailing out")

    sys.exit(return_val)
