#!/usr/bin/env python3

import os
import sys
import logging
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

admin_email_accts = [
                        'commodore@sherbornyachtclub.org',
                        'info@sherbornyachtclub.org',
                        'instruction@sherbornyachtclub.org',
                    ]

waterfront_email_accts = [
                        'waterfront@sherbornyachtclub.org',
                        ]

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

    logging.info("Sheet '%s' available at: %s" % (spreadsheet_title, handler.url))

    email_perms = admin_email_accts + addtl_share_perms
    for email in email_perms:
        handler.share(email, perm_type='user', role='writer', notify=notify_users)

    logging.debug("Found spreadsheet and returning handler to caller")
    return handler

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

def sync_lesson_race(appointment):
    logging.debug("Entering sync_lesson_race")

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in sync_lesson_race was: %s" % year)

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
    gs = get_spreadsheet(spreadsheet_title, waterfront_email_accts)
    logging.debug("Got spreadsheet in sync_lesson_race")
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

def sync_lesson_transaction(appointment):
    logging.debug("Entering sync_lesson_transaction")

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in sync_lesson_transaction was: %s" % year)

    spreadsheet_title = "SYC Lessons and Races Transactions - %s" % year
    spreadsheet_header = spreadsheet_header_lesson_transactions
    logging.debug("Ready to write out header: %s" % spreadsheet_header)

    unscrubbed_worksheet_title = appointment['type']
    logging.debug("Worksheet title before sanitization was: %s" % unscrubbed_worksheet_title)

    worksheet_title = (re.sub(r"\W+|_", " ", unscrubbed_worksheet_title))
    logging.debug("Worksheet title after sanitization was: %s" % worksheet_title)

    try:
        members_spreadsheet = get_spreadsheet("SYC Waterfront - Year %s" % year)
        if members_spreadsheet is None:
            raise SpreadsheetNotFoundError
        members_worksheet = 'Memberships'
        membership = 'Non-Member'

        worksheets = members_spreadsheet.worksheets()

        for sheet in worksheets:
            if sheet.title == members_worksheet:
                logging.debug("FOUND membership sheet: %s" % sheet)

                if sheet.findall(appointment['email']):
                    membership = 'Member'
                    logging.info("Found %s in membership spreadsheet for" % appointment['email'])
                else:
                    logging.info("Didn't find %s in membership spreadsheet for" % appointment['email'])
            else:
                logging.debug("DID NOT FIND membership sheet: %s" % sheet)

    except SpreadsheetNotFoundError:
        logging.warning("Couldn't open up membership spreadsheet for membership verification")

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

    # get the spreadsheet handler
    gs = get_spreadsheet(spreadsheet_title)
    logging.debug("Got spreadsheet in sync_lesson_race")
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

def sync_reservation(appointment):

    year = parsedate.isoparse(appointment['datetime']).year
    logging.debug("Year in sync_reservation was: %s" % year)

    spreadsheet_title = "SYC Waterfront - Year %s" % year
    worksheet_title = 'Reservations'
    spreadsheet_header = spreadsheet_header_waterfront_reservations

    formatted_appt = [
                        appointment['id'],
                        appointment['firstName'] + " " + appointment['lastName'],
                        appointment['email'],
                        appointment['phone'],
                        appointment['date'],
                        appointment['time'],
                        appointment['endTime'],
                        appointment['type'],
                    ]

    # get the spreadsheet handler
    gs = get_spreadsheet(spreadsheet_title, waterfront_email_accts)
    logging.debug("Got spreadsheet in sync_reservation")

    # update the google sheet
    try:
        logging.debug("Writing out to lessons spreadsheet: %s" % formatted_appt)
        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, worksheet_title, spreadsheet_header, formatted_appt))
        append_row_to_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_appt)
    except Exception as e:
        logging.error("Failure updating google sheets: %s" % e)
        return 1

    return 0

def parse_lambda_event(unparsed_event):
    parsed_event = {}

    body = unparsed_event['body']
    parameters = body.split('&')

    for param in parameters:
        label = param.split('=')[0]
        value = param.split('=')[1]
        parsed_event[label] = value

    for label in parsed_event:
        logging.debug(("Figured out parsed_event[label] in parse_lambda_event, value as: %s, %s") % (label, parsed_event[label]))

    logging.debug("Returning parsed_event from parse_lambda_event: %s" % parsed_event)
    return parsed_event

def main(event, context):

    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)

    # Added tests for environment variables
    if (os.environ.get('ACUITY_API_KEY') is None) or (os.environ.get('ACUITY_API_USER') is None):
        logging.critical("Failed to pass either ACUITY_API_USER or ACUITY_API_KEY. Exiting")
        return 1

    appointment = {}
    parsed_event = parse_lambda_event(event)
    try:
        appointment = get_appointment_by_id(parsed_event['id'])
    except requests.exceptions.HTTPError as e:
        logging.critical("Got error from requests call: %s" % e)
        return 1

    if not appointment:
        logging.critical("Got no response from Acuity. Was the id correct?")
        return 1

    logging.debug("appointment['forms'] is %s" % appointment['forms'])

    if appointment['forms'] == []:
        logging.info("Found a calendar event without a form. Forwarding to waterfront reservations")
        # If there's no forms attached, its a reservation
        sync_reservation(appointment)
    else:
        logging.info("Found a calendar event with forms attached. Forwarding to lessons and races")
        # If there are forms attached, its either a race or a lesson
        sync_lesson_race(appointment)
        sync_lesson_transaction(appointment)

    logging.info("Finished")
    return 0

def handler(event, context):
    return main(event, context)

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

    sys.exit(return_val)
