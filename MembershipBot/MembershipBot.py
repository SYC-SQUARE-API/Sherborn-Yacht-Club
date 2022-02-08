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

filter_type_moorings = [
                        'Shoreline',
                        'Water-Row A',
                        'Water-Row B',
                        'Water-Row C',
                        'Water-Row D',
                        'Water-Row E',
                        'Water-Row F',
                        'Water-Row H',
                        'Water-Row I',
                    ]

filter_type_mooring_svcs = [
                        'Mooring Services',
                        ]

filter_type_moorings_all = filter_type_moorings + filter_type_mooring_svcs
filter_type_orders = filter_type_members + filter_type_moorings

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

spreadsheet_header_moorings = [
                        'Order No',
                        'Name',
                        'Email',
                        'Home Phone',
                        'Cell Phone',
                        'Mooring Location',
                        'Mooring Color',
                        'Boat Type',
                        'Boat Color',
                        'Town Permit No',
                    ]

spreadsheet_header_orders = [
                        'Order No',
                        'Primary Name',
                        'Primary Email',
                        'Secondary Name',
                        'Secondary Email',
                        'Membership Type',
                        'Renewal Type',
                        'Fulfillment',
                        'Price',
                        'Discount',
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
                        'Mooring Location',
                        'Mooring Color',
                        'Boat Type',
                        'Boat Color',
                        'Town Permit No',
                        'Mooring Services',
                    ]

spreadsheet_header_transactions = [
                        'Order Id',
                        'Customer Email',
                        'Paid On',
                        'Total',
                        'Tax',
                        'Processing Fees',
                        'Total Net Payment',
                        'Discounts',
                        'Credit Card Type',
                        'Provider',
                        'Voided',
                        'Payment Error',
                    ]

spreadsheet_header_reservations = [
                        'Name',
                        'Email',
                        'Phone',
                        'Date',
                        'Time In',
                        'Time Out',
                        'Reserved On',
                        'Type',
                        'Category',
                        'Canceled',
                        'Checked-In',
                        'Payment Error',
                        'Price',
                    ]

admin_email_accts = [
                        'commodore@sherbornyachtclub.org',
                        'info@sherbornyachtclub.org',
                        'instruction@sherbornyachtclub.org',
                    ]

waterfront_email_accts = [
                        'waterfront@sherbornyachtclub.org',
                        ]

def get_acuity_items(api_endpoint, parameters):
    item_list = []
    schedule_user = os.environ.get('ACUITY_API_USER')
    schedule_key = os.environ.get('ACUITY_API_KEY')

    # define JSON headers, API key pulled from environment variable ACUITY_API_KEY
    headers = {
        "Authorization": "Bearer " + schedule_creds,
        "User-Agent": "MembershipBot"
    }

    return

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

def parse_orders(unparsed_orders, filter_types):
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
                            'mooring_svcs': 'no',
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

            # Check if they bought a mooring
            if line_item['productName'] in filter_type_moorings:
                parsed_order['mooring_location'] = line_item['productName']

                if line_item['variantOptions']:
                    parsed_order['mooring_color'] = line_item['variantOptions'][0]['value']

                if line_item['customizations']:
                    for index, customization in enumerate(line_item['customizations']):
                        for item in customization:
                            if customization['label'] == 'Type of Boat':
                                parsed_order['boat_type'] = customization['value']
                            elif customization['label'] == 'Boat Color':
                                parsed_order['boat_color'] = customization['value']
                            elif customization['label'] == 'Town Boat Permit #':
                                parsed_order['town_permit_no'] = customization['value']

            if line_item['productName'] in filter_type_mooring_svcs:
                parsed_order['mooring_svcs'] = 'Yes'

            if line_item['productName'].endswith(tuple(filter_types)):
                add_member_to_list = True

        if add_member_to_list:
            parsed_orderlist.append(parsed_order)

    return parsed_orderlist

def parse_transactions(unparsed_transactions):
    parsed_tx_list = []

    for tx in unparsed_transactions:
        parsed_transaction = {
                            'order_id': '',
                            'email': '',
                            'voided': '',
                            'total': '',
                            'total_tax': '',
                            'total_netpayment': '',
                            'discounts': '',
                            'payments_error': '',
                            'payments_creditcard': '',
                            'payments_provider': '',
                            'payments_processing_fees': '',
                            'payments_paidon': '',
                            }

        parsed_transaction['order_id'] = tx['salesOrderId']
        parsed_transaction['email'] = tx['customerEmail']
        parsed_transaction['total'] = float(tx['total']['value'])
        parsed_transaction['total_tax'] = float(tx['totalTaxes']['value'])
        parsed_transaction['total_netpayment'] = float(tx['totalNetPayment']['value'])

        if tx['voided']:
            parsed_transaction['voided'] = 'Yes'
        else:
            parsed_transaction['voided'] = 'No'

        if tx['paymentGatewayError']:
            parsed_transaction['payments_error'] = tx['paymentGatewayError']

        try:
            parsed_transaction['discounts'] = float(tx['discounts'][0]['amount']['value'])
        except IndexError:
            pass

        try:
            parsed_transaction['payments_creditcard'] = tx['payments'][0]['creditCardType']
            parsed_transaction['payments_provider'] = tx['payments'][0]['provider']
            parsed_transaction['payments_paidon'] = parsedate.isoparse(tx['payments'][0]['paidOn']).ctime()

            fees = 0
            for fee in tx['payments'][0]['processingFees']:
                fees = fees + float(fee['amount']['value'])
            parsed_transaction['payments_processing_fees'] = fees

        except IndexError:
            pass

        parsed_tx_list.append(parsed_transaction)

    return parsed_tx_list

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
        # only notify users if we had to create a new sheet
        notify_users = True
        handler = client.create(spreadsheet_title)

    #print("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))

    email_perms = admin_email_accts + addtl_share_perms
    for email in email_perms:
        handler.share(email, perm_type='user', role='reader', notify=notify_users)

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

def update_customer_db(database, member_list):

    return 0

def sync_memberships(orders_in_json, year):

    spreadsheet_title = "SYC - Year %s" % year
    worksheet_title = 'Memberships'
    spreadsheet_header = spreadsheet_header_members

    formatted_orders = []
    parsed_orders = parse_orders(orders_in_json, filter_type_members)
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
    gs = get_spreadsheet(spreadsheet_title, waterfront_email_accts)

    # update the google sheet
    # check for column 1 for non-duplicate entries
    try:
        update_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_orders)
    except Exception as e:
        print("failure updating google sheets: %s" % e)
        return 1

    return 0

def sync_moorings(orders_in_json, year):

    spreadsheet_title = "SYC - Year %s" % year
    worksheet_title = 'Moorings'
    spreadsheet_header = spreadsheet_header_moorings

    formatted_orders = []
    parsed_orders = parse_orders(orders_in_json, filter_type_moorings_all)
    for order in parsed_orders:
        formatted_order = [
                            order['order_no'],
                            order['name'],
                            order['email'],
                            order['home_phone'],
                            order['cell_phone'],
                            order['mooring_location'],
                            order['mooring_color'],
                            order['boat_type'],
                            order['boat_color'],
                            order['town_permit_no'],
                            order['mooring_svcs'],
                            ]

        if order['mooring_location'] != '':
            formatted_orders.append(formatted_order)

    for unformatted_order in parsed_orders:
        if ((unformatted_order['mooring_location'] == '') and (unformatted_order['mooring_svcs'] == 'yes')):
            # Loop through the formatted orders list and update for mooring services
            for formatted_order in formatted_orders:
                if unformatted_order['email'] == formatted_order[2]:
                    formatted_order[8] = 'yes'

    if not formatted_orders:
        return 0

    # get the spreadsheet handler
    gs = get_spreadsheet(spreadsheet_title, waterfront_email_accts)

    # update the google sheet
    try:
        update_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_orders)
    except Exception as e:
        print("failure updating google sheets: %s" % e)
        return 1

    return 0

def sync_orders(orders_in_json, year):

    spreadsheet_title = 'SYC Orders'
    worksheet_title = "Year %s" % year
    spreadsheet_header = spreadsheet_header_orders

    formatted_orders = []
    parsed_orders = parse_orders(orders_in_json, filter_type_orders)
    for order in parsed_orders:
        formatted_order = [
                            order['order_no'],
                            order['name'],
                            order['email'],
                            order['secondary_name'],
                            order['secondary_email'],
                            order['membership_type'],
                            order['renewal'],
                            order['fulfillment'],
                            order['price_paid'],
                            order['price_discount'],
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
                            order['mooring_location'],
                            order['mooring_color'],
                            order['boat_type'],
                            order['boat_color'],
                            order['town_permit_no'],
                            order['mooring_svcs'],
                            ]
        formatted_orders.append(formatted_order)

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

def sync_transactions(transacts_in_json, year):

    spreadsheet_title = 'SYC Transactions'
    worksheet_title = "Year %s" % year
    spreadsheet_header = spreadsheet_header_transactions

    formatted_transacts = []
    parsed_transacts = parse_transactions(transacts_in_json)

    for tx in parsed_transacts:
        formatted_tx = [
                            tx['order_id'],
                            tx['email'],
                            tx['payments_paidon'],
                            tx['total'],
                            tx['total_tax'],
                            tx['payments_processing_fees'],
                            tx['total_netpayment'],
                            tx['discounts'],
                            tx['payments_creditcard'],
                            tx['payments_provider'],
                            tx['voided'],
                            tx['payments_error'],
                        ]
        formatted_transacts.append(formatted_tx)

    # get the spreadsheet handler
    gs = get_spreadsheet(spreadsheet_title)

    # update the google sheet
    # check for column 1 for non-duplicate entries
    try:
        update_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_transacts)
    except Exception as e:
        print("Failure updating google sheets: %s" % e)
        return 1

    return 0

def main():
    # Added tests for environment variables
    if os.environ.get('SQUARESPACE_API_KEY') is None:
        print("Failed to pass SQUARESPACE_API_KEY")
        return 1

    #if (os.environ.get('ACUITY_API_USER') is None) or (os.environ.get('ACUITY_API_KEY') is None):
    #    print("Failed to pass either ACUITY_API_USER or ACUITY_API_KEY")
    #    return 1

    orders_api_endpoint = "https://api.squarespace.com/1.0/commerce/orders"
    transactions_api_endpoint = "https://api.squarespace.com/1.0/commerce/transactions"
    schedule_api_endpoint = "https://acuityscheduling.com/api/v1/appointments"

    year = datetime.now().year
    # Process the current year by default. Uncomment below and comment above to get information for previous years
    #year = 2021

    year_beginning = date(year, 1, 1).isoformat()+ 'T00:00:00.0Z'
    year_end = date(year, 12, 30).isoformat()+ 'T00:00:00.0Z'

    # define JSON parameters for the date range to get orders
    request_parameters = {
        "modifiedAfter": year_beginning,
        "modifiedBefore": year_end,
    }

    # Initiate the call to get_squarespace_items which will iterate on pagination
    # the json result will be of result type
    # This applies to Squarespace API requests only
    try:
        json_var = 'result'
        orders_in_json = get_squarespace_items(orders_api_endpoint, json_var, request_parameters)

        if not orders_in_json:
            print("No new orders since the beginning of the year")
            return 0

    except requests.exceptions.HTTPError as error:
        print("Failed to get new members: %s" % error)
        return 1

    # Sync orders
    sync_orders(orders_in_json, year)

    # Sync memberships
    sync_memberships(orders_in_json, year)

    # Sync moorings
    sync_moorings(orders_in_json, year)

    # Get all transactions for specified year
    # the json result will be of documents type
    try:
        json_var = 'documents'
        transactions_in_json = get_squarespace_items(transactions_api_endpoint, json_var, request_parameters)
        if not transactions_in_json:
            print("No transactions since the beginning of the year")
            return 0

    except requests.exceptions.HTTPError as error:
        print("Failed to get new members: %s" % error)
        return 1

    # Sync transactions
    sync_transactions(transactions_in_json, year)

    return 0

def handler(event, context):
    return main()

if __name__ == "__main__":
    return_val = 1
    try:
        return_val = main()
    except KeyboardInterrupt:
        print("Caught a control-C. Bailing out")

    sys.exit(return_val)
