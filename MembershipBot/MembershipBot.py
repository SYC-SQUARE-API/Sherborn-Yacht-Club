#!/usr/bin/env python3


# importing the required libraries
import os
import sys
import gspread
import json
import requests
#from importlib import reload
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta

## function to get a nested list of all member data to be written
## function is recursive to iterate through multiple json pages
def get_members(orders_api_endpoint, parameters):
    member_list = []
    commerce_creds = os.environ.get('SQUARESPACE_API_KEY')

    # define JSON headers, API key pulled from environment variable SQUARESPACE_API_KEY
    headers = {
        "Authorization": "Bearer " + os.environ.get('SQUARESPACE_API_KEY'),
        "User-Agent": "MembershipBot"
    }

    response = requests.get(orders_api_endpoint, headers=headers, params=parameters)
    if response.raise_for_status():
        pass
    else:
        json_data = response.json()

    if response.status_code == requests.codes.ok:
        for member in json_data['result']:
            member_list.append(member)

        if json_data['pagination']['hasNextPage']:
            return (member_list + get_members(json_data['pagination']['nextPageUrl'], None))
    else:
        print("Return status was NOT OK: %s" % response.status_code)
        return False

    return member_list

def parse_members(unparsed_members):
    parsed_memberlist = []

    # create a list of types of memberships
    member_types_list = [   "Family Membership",
                            "Partner Membership",
                            "Individual Membership",
                            "Emeritus Membership",
                            "Junior Membership",
                            "2022 Family Membership",
                            "2022 Partner Membership",
                            "2022 Individual Membership",
                            "2022 Junior Membership",
                        ]

    row_types_list =    [   "Water-Row A",
                            "Water-Row B",
                            "Water-Row C",
                            "Water-Row D",
                            "Water-Row E",
                            "Water-Row F",
                            "Water-Row H",
                            "Water-Row I",
                        ]

    # iterate through every lineItem, which corresponds to an order in the system
    # we further select by only finding orders which correspond to memberships
    for member in unparsed_members:
        parsed_member = {}

        parsed_member['name'] = member['billingAddress']['firstName'] + " " + member['billingAddress']['lastName']
        parsed_member['email'] = member['customerEmail']
        parsed_member['street_address'] = member['billingAddress']['address1']
        parsed_member['city'] = member['billingAddress']['city']
        parsed_member['state'] = member['billingAddress']['state']
        parsed_member['zipcode'] = member['billingAddress']['postalCode']
        parsed_member['created_on'] = member['createdOn']
        parsed_member['fulfilled'] = member['fulfillmentStatus']
        parsed_member['price_paid'] = member['grandTotal']['value']
        parsed_member['discount_price'] = member['discountTotal']['value']

        for line_item in member['lineItems']:
            # Check if they bought a membership
            if line_item['productName'] in member_types_list:
                parsed_member['membership_type'] = line_item['productName']

                if line_item['customizations']:
                    for index, customization in enumerate(line_item['customizations']):
                        for item in customization:
                            if customization['label'] == 'Confirm Membership Type':
                                parsed_member['renewal'] = customization['value']
                            elif customization['label'] == 'Primary Member Name':
                                parsed_member['primary_member'] = customization['value']
                            elif customization['label'] == 'Cell Phone':
                                parsed_member['cell_phone'] = customization['value'].strip()
                            elif customization['label'] == 'Primary Address':
                                parsed_member['home_address'] = customization['value']
                            elif customization['label'] == 'Secondary Member Name':
                                parsed_member['secondary_member'] = customization['value']
                            elif customization['label'] == 'Secondary Member Email':
                                parsed_member['secondary_email'] = customization['value']
                            elif customization['label'] == 'Emergency Contact Name':
                                parsed_member['emergency_contact_name'] = customization['value']
                            elif customization['label'] == 'Emergency Contact Phone':
                                parsed_member['emergency_contact_phone'] = customization['value'].strip()
                            elif (customization['label'] == 'Child Family Member #1'):
                                parsed_member['child_member_1'] = {}
                                parsed_member['child_member_1']['name'] = line_item['customizations'][index][item]
                                parsed_member['child_member_1']['dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #2'):
                                parsed_member['child_member_2'] = {}
                                parsed_member['child_member_2']['name'] = line_item['customizations'][index][item]
                                parsed_member['child_member_2']['dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #3'):
                                parsed_member['child_member_3'] = {}
                                parsed_member['child_member_3']['name'] = line_item['customizations'][index][item]
                                parsed_member['child_member_3']['dob'] = line_item['customizations'][index+1][item]
                            elif (customization['label'] == 'Child Family Member #4'):
                                parsed_member['child_member_4'] = {}
                                parsed_member['child_member_4']['name'] = line_item['customizations'][index][item]
                                parsed_member['child_member_4']['dob'] = line_item['customizations'][index+1][item]
            # Check if they bought a mooring
            if line_item['productName'] in row_types_list:
                parsed_member['boat_registration'] = {}
                parsed_member['boat_registration']['mooring'] = line_item['productName']
                parsed_member['boat_registration']['mooring_color'] = line_item['variantOptions'][0]['value']

                if line_item['customizations']:
                    for index, customization in enumerate(line_item['customizations']):
                        for item in customization:
                            if customization['label'] == 'Type of Boat':
                                parsed_member['boat_registration']['type_of_boat'] = customization['value']
                            elif customization['label'] == 'Boat Color':
                                parsed_member['boat_registration']['boat_color'] = customization['value']
                            elif customization['label'] == 'Town Boat Permit #':
                                parsed_member['boat_registration']['town_permit_no'] = customization['value']

            # Check if they added mooring services
            if line_item['productName'] == 'Mooring Services':
                parsed_member['mooring_svcs'] = True

        parsed_memberlist.append(parsed_member)

    return parsed_memberlist

def get_spreadsheet(spreadsheet_name):
    # define the scope
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

    # add credentials to the account
    credentials = ServiceAccountCredentials.from_json_keyfile_name('googleCreds.json', scope)

    # authorize the clientsheet
    client = gspread.authorize(credentials)

    # get the instance of the Spreadsheet
    return client.open(spreadsheet_name)

def update_spreadsheet(spreadsheet, member_list):

    # make a spreadsheet for the year if necessary
    # set the target_sheet for the sheet we'll be writing to
    worksheets = spreadsheet.worksheets()

    target_sheet = None
    current_year = date.today().year

    for sheet in worksheets:
        if sheet.title == "Year %s" % current_year:
            target_sheet = sheet

    # If sheet was not found create it
    if not target_sheet:
        target_sheet = spreadsheet.add_worksheet(title="Year %s" % current_year, rows=1, cols=30)
        target_sheet.append_row([   'Primary Name',
                                    'Primary Email',
                                    'Secondary Name',
                                    'Secondary Email',
                                    'Membership Type',
                                    'Renewal Type',
                                    'Price',
                                    'Discount',
                                    'Home Address',
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
                                    'Mooring Location',
                                    'Mooring Color',
                                    'Mooring Services',
                                    'Boat Type',
                                    'Boat Color',
                                    'Permit No',
                                ], value_input_option='USER-ENTERED', table_range='A1:B1')

    # write to the google doc
    start_row = target_sheet.row_count + 1

    new_members = []
    for person in member_list:
        formatted_person = [    person['name'],
                                person['email'],
                                person['secondary_member'] if 'secondary_member' in person.keys() else '',
                                person['secondary_email'] if 'secondary_email' in person.keys() else '',
                                person['membership_type']if 'membership_type' in person.keys() else '',
                                person['renewal'] if 'renewal' in person.keys() else '',
                                person['price_paid'] if 'price_paid' in person.keys() else '',
                                person['discount_price'] if 'discount_price' in person.keys() else '',
                                person['home_address'] if 'home_address' in person.keys() else '',
                                person['cell_phone'] if 'cell_phone' in person.keys() else '',
                                person['emergency_contact_name'] if 'emergency_contact_name' in person.keys() else '',
                                person['emergency_contact_phone'] if 'emergency_contact_phone' in person.keys() else '',
                                person['child_member_1']['name'] if 'child_member_1' in person.keys() else '',
                                person['child_member_1']['dob'] if 'child_member_1' in person.keys() else '',
                                person['child_member_2']['name'] if 'child_member_2' in person.keys() else '',
                                person['child_member_2']['dob'] if 'child_member_2' in person.keys() else '',
                                person['child_member_3']['name'] if 'child_member_3' in person.keys() else '',
                                person['child_member_3']['dob'] if 'child_member_3' in person.keys() else '',
                                person['child_member_4']['name'] if 'child_member_4' in person.keys() else '',
                                person['child_member_4']['dob'] if 'child_member_4' in person.keys() else '',
                                person['boat_registration']['mooring'] if 'boat_registration' in person.keys() else '',
                                person['boat_registration']['mooring_color'] if 'boat_registration' in person.keys() else '',
                                person['mooring_svcs'] if 'mooring_svcs' in person.keys() else '',
                                person['boat_registration']['type_of_boat'] if 'boat_registration' in person.keys() else '',
                                person['boat_registration']['boat_color'] if 'boat_registration' in person.keys() else '',
                                person['boat_registration']['town_permit_no'] if 'boat_registration' in person.keys() else '',
                            ]

        new_members.append(formatted_person)

    target_sheet.append_rows(new_members, value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    target_sheet.columns_auto_resize(0, 30)

    return True

def update_customer_db(database, member_list):

    return

## main code begin ##

def handler(event, context):
    # definte variables
    orders_api_endpoint = "https://api.squarespace.com/1.0/commerce/orders"
    scheduled_sync_days = 1
    syc_spreadsheet = 'Brent Testing'

    # Added tests for environment variables
    if os.environ.get('SQUARESPACE_API_KEY') is None:
        print("Failed to pass SQUARESPACE_API_KEY")
        return 1

    # define JSON parameters
    parameters = {
        "modifiedAfter": (datetime.now() - timedelta(days=scheduled_sync_days)).isoformat() + 'Z',
        "modifiedBefore": datetime.now().isoformat() + 'Z',
        "fulfillmentStatus": "FULFILLED"
    }

    # Initiate the call to get_members which will iterate on pagination
    try:
        raw_members = get_members(orders_api_endpoint, parameters)
    except requests.exceptions.HTTPError as error:
        print("Failed to get new members: %s" % error)
        return 1

    if raw_members:
        scrubbed_members = parse_members(raw_members)
    else:
        print("No new members since %s day(s) ago" % scheduled_sync_days)
        return 0

    # get the spreadsheet handler
    gs = get_spreadsheet(syc_spreadsheet)

    ## write new_members to google sheet ##
    try:
        update_spreadsheet(gs, scrubbed_members)
    except Exception as e:
        print("Failure updating Google Sheets: %s" % e)
        return 1

    return 0

if __name__ == "__main__":
    return_val = 1
    try:
        return_val = handler(None, None)
    except KeyboardInterrupt:
        print("Caught a control-C. Bailing out")

    sys.exit(return_val)
