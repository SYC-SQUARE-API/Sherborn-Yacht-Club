# importing the required libraries
import gspread
import json
import requests
from importlib import reload
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, timedelta

gspread = reload(gspread)

## function definitions ##

## function to get a nested list of all member data to be written
## function is recursive to iterate through multiple json pages
## accepts three arguments, new_members a nested list, a JSON http string, and a boolean for if it's the first loop
def get_members(new_members, json_string, first):

    commerce_creds = open('commerceCreds.txt', 'r')

    # define JSON headers, these creds should be pulled from somewhere
    headers = {
        "Authorization": commerce_creds.readline(),
        "User-Agent": "MembershipBot"
    }

    # get the past 24 hours of orders, 10am UTC corresponds to 5am EST
    todays_date = date.today()
    modified_after = str(todays_date - timedelta(days=1)) + "T10:00:00Z"
    modified_before = str(todays_date) + "T10:00:00Z"

    # define JSON parameters
    parameters = {
        "modifiedAfter": modified_after,
        "modifiedBefore": modified_before,
        "fulfillmentStatus": "FULFILLED"
    }

    # for testing only
    #parameters = {
    #    "modifiedAfter": "2021-01-01T12:00:00Z",
    #    "modifiedBefore": "2021-12-31T12:00:00Z",
    #    "fulfillmentStatus": "FULFILLED"
    #}

    # fetch JSON page, the first run will need to provide parameters
    if first == True:
        response = requests.get(json_string, headers=headers, params=parameters)
    else: 
        response = requests.get(json_string, headers=headers)

    # load JSON into a map variable
    member_dict = response.json()

    # create a list of types of memberships
    member_types_list = ["Family Membership", "Partner Membership", "Individual Membership", "Emeritus Membership", "Junior Membership", "2022 Family Membership", "2022 Partner Membership", "2022 Individual Membership", "2022 Junior Membership"]

    # iterate through every lineItem, which corresponds to an order in the system
    # we further select by only finding orders which correspond to memberships
    for x in member_dict['result']:
        for y in x['lineItems']:
            nl_membership_type = y['productName']
            if nl_membership_type in member_types_list:
                # collect all fields to create a new line
                # customizations is not valid for all types and is sometimes null
                if y['customizations'] == None:
                    nl_renewal_type = ""
                else:
                    nl_renewal_type = y['customizations'][0]['value']

                # these fields apply to all types
                nl_primary_name = x["billingAddress"]['firstName'] + " " + x["billingAddress"]['lastName']
                nl_primary_email = x["customerEmail"]
                nl_membership_price = y['unitPricePaid']['value']

                # family membership check
                if nl_membership_type == member_types_list[0] or  nl_membership_type == member_types_list[5]:
                    nl_secondary_name = y['customizations'][6]['value']
                    nl_secondary_email = y['customizations'][7]['value']
                # partner membership check
                elif nl_membership_type == member_types_list[1] or nl_membership_type == member_types_list[6]:
                    nl_secondary_name = y['customizations'][5]['value']
                    nl_secondary_email = y['customizations'][6]['value']
                # all other membership types
                else:
                    nl_secondary_name = ""
                    nl_secondary_email = ""

                # emritus and junior do not have a renewal type radio button
                if nl_membership_type == member_types_list[3] or nl_membership_type == member_types_list[4] or nl_membership_type == member_types_list[8]:
                    nl_renewal_type = ""

                # create a new line
                new_line = [nl_renewal_type, nl_primary_name, nl_primary_email, nl_secondary_name, nl_secondary_email, nl_membership_type, nl_membership_price]

                # add the new line to our new_members list
                new_members.append(new_line)
    
    # if there is an additional page of results, recursively iterate
    if member_dict['pagination']['nextPageUrl'] != None:
        new_members = get_members(new_members, member_dict['pagination']['nextPageUrl'], False)

    # return the new_members nested list
    return new_members

## main code begin ##

def main(event, handler):
    # definte variables
    new_members = []
    json_string = "https://api.squarespace.com/1.0/commerce/orders"

    # call member function
    new_members = get_members(new_members, json_string, True)

    ## write new_members to google sheet ##

    # define the scope
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

    # add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name('googleCreds.json', scope)

    # authorize the clientsheet 
    client = gspread.authorize(creds)

    # get the instance of the Spreadsheet
    spreadsheet = client.open('Membership Test')

    # grab date info (maybe move up)
    todays_date = date.today()

    # make a spreadsheet for the year if necessary
    # set the target_sheet for the sheet we'll be writing to
    sheet_array = spreadsheet.worksheets()
    sheet_found = False

    for sheet in sheet_array:
        if sheet.title == str(todays_date.year):
            target_sheet = sheet
            sheet_found = True
            break

    if sheet_found == False:
        target_sheet = spreadsheet.add_worksheet(str(todays_date.year), 1, 7, index=0)
        target_sheet.append_row(['Renewal Type', 'Primary Name', 'Primary Email', 'Secondary Name', 'Secondary Email', 'Membership Type', 'Price'], value_input_option='USER-ENTERED', table_range='A1:B1')
        # update sheet_array
        sheet_array = spreadsheet.worksheets()
        target_sheet = sheet_array[0]

    # write to the google doc
    start_row = target_sheet.row_count + 1
    target_sheet.append_rows(new_members, value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    target_sheet.columns_auto_resize(0, 7)

    # check code finished
    print('end')
    return 0
