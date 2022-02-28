#!/usr/bin/env python3

import base64
import os
import sys
import logging
import google
import gspread
import stripe
import json
import requests
import logging
import re
from requests.auth import HTTPBasicAuth
from gspread.exceptions import *
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
from dateutil import parser as parsedate


spreadsheet_header_waterfront_lessons = [
                        'Order Id',
                        'Name',
                        'Email',
                        'Phone',
                        'Date Requested',
                    ]

spreadsheet_header_waterfront_reservations = [
                        'Order Id',
                        'Name',
                        'Email',
                        'Phone',
                        'Date Requested',
                        'Time In',
                        'Time Out',
                        'Type',
                        'Member Status',
                    ]

spreadsheet_header_lesson_transactions = [
                        'Order Id',
                        'Name',
                        'Email',
                        'Phone',
                        'Order Placed',
                        'List Price',
                        'Amount Paid',
                        'Paid',
                        'Member Status',
                    ]

spreadsheet_header_transactions_ledger = [
                        'Order Id',
                        'Name',
                        'Email',
                        'Phone',
                        'Type',
                        'Order Placed',
                        'List Price',
                        'Amount Paid',
                        'Paid',
                        'Member Status',
                    ]

admin_email_accts = [
                        'commodore@sherbornyachtclub.org',
                        'info@sherbornyachtclub.org',
                        'instruction@sherbornyachtclub.org',
                    ]

waterfront_email_accts = [
                        'waterfront@sherbornyachtclub.org',
                        ]

# get Google auth client
# returns client
# will not cause exception unless an action is performed against the API. that's nice
def auth_google(credentials):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials, scope)
    client = gspread.authorize(credentials)

    return client

# create a spreadsheet, takes spreadsheet title, and optional notify users on creation boolean
# returns spreadsheet handler
def create_spreadsheet(client, spreadsheet_title, notify_users=False, addtl_share_perms=None):

    handler = client.create(spreadsheet_title)
    logging.info("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))

    for email in admin_email_accts:
        handler.share(email, perm_type='user', role='writer', notify=notify_users)

    if addtl_share_perms is not None:
        for email in addtl_share_perms:
            handler.share(email, perm_type='user', role='reader', notify=notify_users)

    return handler

# get spreadsheet but cause exception if failed
# returns handler if succesful
def get_spreadsheet(client, spreadsheet_title):

    handler = client.open(spreadsheet_title)

    logging.info("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))
    logging.debug("Retrieved spreadsheet and returning handler to caller")
    return handler

# get spreadsheet but handle exception and create spreadsheet automatically if failed
# returns handler if succesful
def get_or_create_spreadsheet(client, spreadsheet_title, notify_users=False, addtl_share_perms=None):

    try:
        handler = client.open(spreadsheet_title)
    except:
        handler = create_spreadsheet(client, spreadsheet_title, notify_users, addtl_share_perms)

    logging.info("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))
    logging.debug("Retrieved spreadsheet and returning handler to caller")
    return handler

# remove a row from spreadsheet, required spreadsheet title, worksheet id, and the row in int
# returns True if successful
def remove_row_from_spreadsheet(client, spreadsheet_title, worksheet_id, row):
    logging.debug("Entering remove_row_from_spreadsheet")

    logging.debug("Row value is: %s" % row)

    gs = get_spreadsheet(client, spreadsheet_title)
    worksheet = gs.get_worksheet_by_id(worksheet_id)
    logging.debug("Worksheet opened: %s" % worksheet)

    # Check to see if it's just the header row and the item, or just the row to be deleted itself
    if ((worksheet.row_count <= 2) and (worksheet.frozen_row_count == 1)) or worksheet.row_count == 1:
        logging.info("This remove_rows is going to fail because there are %s rows in sheet. I'm going to remove the worksheet entirely" % worksheet.row_count)
        gs.del_worksheet(worksheet)

    else:
        try:
            result = worksheet.delete_rows(row)
            logging.debug("Deleted row: %s" % row)
        except gspread.exceptions.APIError as api_error:
            logging.warning("Got Google API error: %s" % api_error)
            return False

    logging.info("Appointment removed")
    return True

# update the row, required spreadsheet title, worksheet id, the row in int, appointment dictionary returned by find_order_by_id
# returns True if successful
def update_row_in_spreadsheet(client, spreadsheet_title, worksheet_id, row, appointment):
    logging.debug("Entering update_row_in_spreadsheet")

    logging.debug("Row value is: %s" % row)

    gs = get_spreadsheet(client, spreadsheet_title)
    worksheet = gs.get_worksheet_by_id(worksheet_id)
    logging.debug("Worksheet opened: %s" % worksheet)

    try:
        for index, value in enumerate(appointment):
            # write at index+1 because google sheet columns start at 1, indexes start at 0
            logging.debug("Updating row %s, cell %s with value %s: " % (row, index+1, value))
            worksheet.update_cell(row, index+1, value)

        logging.debug("Updated row: %s" % row)
    except gspread.exceptions.APIError as api_error:
        logging.warning("Got Google API error: %s" % api_error)
        return False

    logging.info("Appointment updated")
    return True

# add a row to the spreadsheet. required spreadsheet handler, worksheet title, header row, and a formatted row to add in list
# returns True if successful
def append_row_to_spreadsheet(spreadsheet, worksheet_title, header_row, row_to_add):
    logging.debug("Entering append_row_to_spreadsheet")

    # make a spreadsheet for the year if necessary
    # set the target_sheet for the sheet we'll be writing to
    worksheets = spreadsheet.worksheets()

    target_sheet = None
    for sheet in worksheets:
        if sheet.title == worksheet_title:
            logging.debug("Found target_sheet: %s" % target_sheet)
            target_sheet = sheet

    logging.debug("target_sheet is: %s" % target_sheet)

    # If sheet was not found create it
    if target_sheet is None:
        logging.warning("Couldn't find worksheet %s. Creating" % worksheet_title)
        target_sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1, cols=len(row_to_add))
        target_sheet.append_row(header_row, value_input_option='USER-ENTERED')
    else:
        logging.debug("Found target_sheet: %s" % target_sheet)

    logging.debug("Ready to append_row: %s" % row_to_add)
    start_row = 1
    target_sheet.append_row(row_to_add, value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    target_sheet.columns_auto_resize(0, len(row_to_add))
    target_sheet.freeze(rows=1)
    logging.info("Updated Google Sheet successfully")

    return True

## function to get a nested list of all orders from squarespace
## returns: dictionary of orders from json result
def get_appointment_by_id(id):
    api_endpoint = 'https://acuityscheduling.com/api/v1/appointments/'

    user = os.environ.get('ACUITY_API_USER')
    api_key = os.environ.get('ACUITY_API_KEY')

    headers = {
        "User-Agent": "ScheduleBot"
    }

    response = requests.get(api_endpoint + str(id), headers=headers, auth=HTTPBasicAuth(user, api_key))
    if response.raise_for_status():
        pass
    else:
        json_data = response.json()

    if response.status_code == requests.codes.ok:
        appointment = json_data
    else:
        logging.error("Return status from response was requests.get was NOT OK: %s" % response.status_code)
        appointment = {}

    logging.debug("Returning appointment from get_appointment_by_id: %s" % appointment)
    return appointment

# function to find order by id in int. takes in order id in int, and list of spreadsheet names to search
# returns tuples of spreadsheet title, worksheet id, and row id in int if found
def find_order_by_id(client, order_id, spreadsheet_names):
    # This functions expects an order id in the form of a string and a list of spreadsheet names to go looking in
    found = False

    logging.debug("Started find_order_by_id with id: %s and spreadsheet_names: %s" % (order_id, spreadsheet_names))

    for spreadsheet in spreadsheet_names:
        # get the instance of the Spreadsheet
        try:
            gs = client.open(spreadsheet)
            logging.debug("Opened sheet '%s' available at: %s" % (spreadsheet, gs.url))

            worksheets = gs.worksheets()
            logging.debug("Got worksheets of: %s" % worksheets)

            print("Spreadsheet title is: %s" % spreadsheet)

            logging.debug("Now hunting for order id %s in worksheets: %s" % (order_id, worksheets))
            for worksheet in worksheets:
                logging.debug("Opening worksheet: %s" % worksheet)
                cell = worksheet.find(str(order_id), in_column=1)
                if cell:
                    found = True
                    spreadsheet_title = spreadsheet
                    worksheet_id = worksheet.id
                    row = cell
                    logging.debug("Found order and returning: %s, %s, %s" % (spreadsheet_title, worksheet_id, row))

        except SpreadsheetNotFound:
            logging.warning("Got an error trying to open spreadsheet %s in worksheets: %s")
            pass

    if found is False:
        logging.debug("Returning: %s" % found)
        return None

    logging.debug("Returning: %s, %s, %s" % (spreadsheet_title, worksheet_id, row))

    return (spreadsheet_title, worksheet_id, row)

# verifies membership. takes in email in string returned from find_order_by_id dictionary and year
# returns True if found in the membership spreadsheet
def verify_member(client, email, year):
    found = False

    logging.debug("Started verify_member with email: %s" % email)

    try:
        logging.debug("Opening spreadsheet: SYC Waterfront - Year %s" % year)
        members_spreadsheet = get_spreadsheet(client, "SYC Waterfront - Year %s" % year)
        members_worksheet = 'Memberships'
        worksheets = members_spreadsheet.worksheets()

        for sheet in worksheets:
            if sheet.title == members_worksheet:
                logging.debug("FOUND membership sheet: %s" % sheet)

                if sheet.findall(email):
                    found = True
                    logging.info("Found %s in membership spreadsheet for" % email)
                else:
                    logging.info("Didn't find %s in membership spreadsheet for" % email)
            else:
                logging.debug("DID NOT FIND membership sheet: %s" % sheet)

    except ValueError:
        logging.warning("Couldn't open up membership spreadsheet for membership verification")

    return found

# add lesson or race to the spreadsheet. takes in dictionary appointment returned by find_order_by_id
# returns true if successful
def add_lesson_race(client, appointment):
    logging.debug("Entering add_lesson_race")

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in add_lesson_race was: %s" % year)

    spreadsheet_title = "SYC Sailing Lessons and Races - %s" % year
    spreadsheet_header = spreadsheet_header_waterfront_lessons

    unscrubbed_worksheet_title = appointment['type']
    logging.debug("Worksheet title before sanitization was: %s" % unscrubbed_worksheet_title)

    worksheet_title = (re.sub(r"\W+|_", " ", unscrubbed_worksheet_title))
    logging.debug("Worksheet title after sanitization was: %s" % worksheet_title)

    formatted_appt = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['date'],
                    ]

    for form in appointment['forms']:
        logging.info("Parsing through the forms and adding them to the spreadsheet")
        logging.debug("FOUND FORM: %s" % form)

        for question in form['values']:
            logging.debug("FOUND QUESTION: %s" % question['name'])
            spreadsheet_header.append(question['name'])
            logging.debug("FOUND RESPONSE: %s" % question['value'])
            formatted_appt.append(question['value'])

    # get the spreadsheet handler
    gs = get_or_create_spreadsheet(client, spreadsheet_title)

    logging.debug("Got spreadsheet in add_lesson_race")
    logging.debug("Ready to write out header: %s" % spreadsheet_header)

    logging.debug("Ready to write out row: %s" % formatted_appt)
    # update the google sheet
    try:
        logging.debug("Writing out to lessons spreadsheet: %s" % formatted_appt)
        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, worksheet_title, spreadsheet_header, formatted_appt))
        append_row_to_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_appt)
    except Exception as e:
        logging.error("Failure updating google sheets: %s" % e)
        return 1

    return 0

# add lesson or race transaction to the spreadsheet. takes in dictionary appointment returned by find_order_by_id
# returns true if successful
def add_lesson_transaction(client, appointment):
    logging.debug("Entering add_lesson_transaction")

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in add_lesson_transaction was: %s" % year)

    spreadsheet_title = "SYC Lessons and Races Transactions - %s" % year
    spreadsheet_header = spreadsheet_header_lesson_transactions
    logging.debug("Ready to write out header: %s" % spreadsheet_header)

    unscrubbed_worksheet_title = appointment['type']
    logging.debug("Worksheet title before sanitization was: %s" % unscrubbed_worksheet_title)

    worksheet_title = (re.sub(r"\W+|_", " ", unscrubbed_worksheet_title))
    logging.debug("Worksheet title after sanitization was: %s" % worksheet_title)

    # Default to non-member, revise if we find them
    membership = 'Non-Member'

    if verify_member(client, appointment['email'], year):
        membership = 'Member'

    # Write out the transaction in a worksheet specific to the class
    formatted_appt = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['date'],
                        "$" + str(float(appointment['price'])),
                        "$" + str(float(appointment['amountPaid'])),
                        appointment['paid'],
                        membership,
                    ]

    # Also write out the transaction in a worksheet with the general ledger
    ledger_title = 'All Transactions'
    ledger_header = spreadsheet_header_transactions_ledger

    formatted_transaction = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['type'],
                        appointment['date'],
                        "$" + str(float(appointment['price'])),
                        "$" + str(float(appointment['amountPaid'])),
                        appointment['paid'],
                        membership,
                    ]

    # get the spreadsheet handler
    gs = get_or_create_spreadsheet(client, spreadsheet_title)
    logging.debug("Got spreadsheet in add_lesson_race")
    logging.debug("Ready to write out header: %s" % spreadsheet_header)

    logging.debug("Ready to write out row: %s" % formatted_appt)
    # update the google sheet
    try:
        logging.debug("Writing out to lessons spreadsheet: %s" % formatted_appt)

        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, worksheet_title, spreadsheet_header, formatted_appt))
        append_row_to_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_appt)

        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, ledger_title, ledger_header, formatted_transaction))
        append_row_to_spreadsheet(gs, ledger_title, ledger_header, formatted_transaction)

    except Exception as e:
        logging.error("Failure updating google sheets: %s" % e)
        return 1

    return 0

# add reservation to the waterfront spreadsheet. takes in dictionary appointment returned by find_order_by_id
# returns true if successful
def add_reservation(client, appointment):

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in add_reservation was: %s" % year)

    spreadsheet_title = "SYC Waterfront - Year %s" % year
    worksheet_title = 'Reservations'
    spreadsheet_header = spreadsheet_header_waterfront_reservations

    membership = 'Non-Member'
    if verify_member(client, appointment['email'], year):
        membership = 'Member'

    formatted_appt = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['date'],
                        appointment['time'],
                        appointment['endTime'],
                        appointment['type'],
                        membership,
                    ]

    # get the spreadsheet handler
    gs = get_or_create_spreadsheet(client, spreadsheet_title, addtl_share_perms=waterfront_email_accts)
    logging.debug("Got spreadsheet in add_reservation")

    # update the google sheet
    try:
        logging.debug("Writing out to lessons spreadsheet: %s" % formatted_appt)
        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, worksheet_title, spreadsheet_header, formatted_appt))
        append_row_to_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_appt)
    except Exception as e:
        logging.error("Failure updating google sheets: %s" % e)
        return 1

    return 0

# updates a reservation. takes in dictionary appointment returned by find_order_by_id
# returns true if successful
def update_appointment(client, appointment):

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in update_appointment was: %s" % year)

    spreadsheet_titles = [
                            "SYC Waterfront - Year %s" % year,
                            "SYC Sailing Lessons and Races - %s" % year,
                            ]

    # get the spreadsheet information
    try:
        (spreadsheet, worksheet_id, cell) = find_order_by_id(client, appointment['id'], spreadsheet_titles)
        logging.debug("FOUND IT!")
    except TypeError:
        logging.warning("Could not find order in find_order_by_id")
        return 1

    # Parse the updated appointment into the same format as we expect
    # Sailing and racing appointments include forms, where reservations do not
    # This is where we add the additional fields with forms if forms is defined
    # Otherwise we assume it's a reservation and add time, endTime, and type

    membership = 'Non-Member'
    if verify_member(client, appointment['email'], year):
        membership = 'Member'

    formatted_appt = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['date'],
                    ]

    if appointment['forms'] != []:
        for form in appointment['forms']:
            logging.info("Parsing through the forms and adding them to the spreadsheet")
            logging.debug("FOUND FORM: %s" % form)

            for question in form['values']:
                logging.debug("FOUND QUESTION: %s" % question['name'])
                logging.debug("FOUND RESPONSE: %s" % question['value'])
                formatted_appt.append(question['value'])

    else:
        formatted_appt.append(appointment['time'])
        formatted_appt.append(appointment['endTime'])
        formatted_appt.append(appointment['type'])
        formatted_appt.append(membership)

    # Time to remove the row from the sheet
    if not update_row_in_spreadsheet(client, spreadsheet, worksheet_id, cell.row, formatted_appt):
        logging.info("Updated row %s from spreadsheet %s worksheet %s with values: %s" % (cell.row, spreadsheet, worksheet_id, formatted_appt))

    return 0

# removes a reservation. takes in dictionary appointment returned by find_order_by_id
# returns true if successful
def remove_appointment(client, appointment):

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in remove_appointment was: %s" % year)

    spreadsheet_titles = [
                            "SYC Waterfront - Year %s" % year,
                            "SYC Sailing Lessons and Races - %s" % year,
                            ]

    # get the spreadsheet information
    try:
        (spreadsheet, worksheet_id, cell) = find_order_by_id(client, appointment['id'], spreadsheet_titles)
        logging.debug("FOUND IT!")
    except TypeError:
        logging.warning("Could not find order in find_order_by_id")
        return 1

    # Time to remove the row from the sheet

    if not remove_row_from_spreadsheet(client, spreadsheet, worksheet_id, cell.row):
        logging.info("Removed cell %s from spreadsheet %s worksheet %s" % (cell, spreadsheet, worksheet_id))

    return 0

# parse out the string that is received by lambda in the body of the json document
# returns a dictionary that includes action, id, appointmentTypeID, calendarID
# we ignore everything but the action and the id because reasons
def parse_lambda_event(unparsed_event):
    logging.debug("Entering parse_lambda_event")

    if unparsed_event['isBase64Encoded']:
        logging.debug("Decoding from Lambda: %s" % unparsed_event['body'])
        body = base64.b64decode(unparsed_event['body']).decode('ascii')
    else:
        logging.debug("Decoding from test harness: %s" % unparsed_event['body'])
        body = unparsed_event['body']

    parameters = body.split('&')
    parsed_event = {}

    for param in parameters:
        label = param.split('=')[0]
        value = param.split('=')[1]
        parsed_event[label] = value

    for label in parsed_event:
        logging.debug(("Figured out parsed_event[label] in parse_lambda_event, value as: %s, %s") % (label, parsed_event[label]))

    logging.debug("Returning parsed_event from parse_lambda_event: %s" % parsed_event)
    return parsed_event

# enter the main event
def main(event, context):

    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)

    # Added tests for environment variables
    if (os.environ.get('ACUITY_API_KEY') is None) or (os.environ.get('ACUITY_API_USER') is None):
        logging.critical("Failed to pass either ACUITY_API_USER or ACUITY_API_KEY. Exiting")
        return 1

    google_credentials_file = 'googleCreds.json'

    if os.path.exists(google_credentials_file):
        logging.info("Found Google credentials file")
    else:
        logging.critical("Could not find Google credentials file: %s. Exiting" % google_credentials_file)
        return 1

    try:
        client = auth_google(google_credentials_file)
        # testing if Google client handler works
        logging.info("Testing Google client handler")
        client.openall()
    except ValueError:
        # ValueError if bad file
        logging.critical("Could not authenticate to Google. Your credentials file appears mangled")
        return 1
    except google.auth.exceptions.RefreshError as google_error:
        logging.critical("Could not authenticate to Google: %s \nCheck your credentials. Exiting" % google_error)
        return 1

    appointment = {}
    parsed_event = parse_lambda_event(event)
    action = parsed_event['action']

    try:
        appointment = get_appointment_by_id(parsed_event['id'])
    except requests.exceptions.HTTPError as e:
        logging.critical("Got error from requests call: %s" % e)
        return 1

    if not appointment:
        logging.critical("Got no response from Acuity for id: %s. Was the id correct?" % parsed_event['id'])
        return 1

    logging.debug("appointment['forms'] is %s" % appointment['forms'])

    logging.info("Got an action of %s" % action)
    if action == 'scheduled':
        if appointment['forms'] == []:
            logging.info("Found a calendar event without a form. Forwarding to waterfront reservations")
            # If there's no forms attached, its a reservation
            add_reservation(client, appointment)
        else:
            logging.info("Found a calendar event with forms attached. Forwarding to lessons and races")
            # If there are forms attached, its either a race or a lesson
            add_lesson_race(client, appointment)
            add_lesson_transaction(client, appointment)

    elif action == 'canceled':
        logging.info("Caught a canceled event. Forwarding to remove_appointment")
        # if canceled we'll need to look for the event id in the waterfront spreadsheet/reservations worksheet, and the lessons spreadsheet/all worksheets for the order id
        remove_appointment(client, appointment)

    elif action == 'rescheduled' or action == 'changed':
        logging.info("Caught a rescheduled or changed event. Forwarding to update_appointment")
        update_appointment(client, appointment)

    elif action == 'order.completed':
        # Add to the transaction log
        logging.info("Caught order.completed. Adding the appointment to the transaction log")
        add_lesson_transaction(client, appointment)

    else:
        logging.warning("Caught an unhandled action. Not doing anything with it.")


    logging.info("Finished")
    return 0

def handler(event, context):
    return_value = main(event, context)
    status_code = 200

    if return_value > 0:
        return_string = "Executed with issues: %s" % return_value
    else:
        return_string = "Success"

    response = {
                    "statusCode": status_code,
                    "body": return_string,
                }

    logging.debug("Returning response of: %s" % json.dumps(response))
    return json.dumps(response)

if __name__ == "__main__":
    return_val = 1

    try:
        test_event_handler = open('event.json')
        test_event = json.load(test_event_handler)
        test_event_handler.close()
    except FileNotFoundError as e:
        logging.warning("Caught error opening test file: %s" % e)
        sys.exit(return_val)

    context = None

    try:
        return_val = main(test_event, context)
    except KeyboardInterrupt:
        logging.critical("Caught a control-C. Bailing out")

    logging.debug("Exiting test harness with %s" % return_val)
    sys.exit(return_val)
