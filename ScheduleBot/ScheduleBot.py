#!/usr/bin/env python3

import os
import sys
import logging
import gspread
import stripe
import json
import requests
import logging
from requests.auth import HTTPBasicAuth
from gspread.exceptions import *
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
from dateutil import parser as parsedate


spreadsheet_header_waterfront_lessons = [
                        'Name',
                        'Phone',
                        'Email',
                        'Swim Ability',
                        'Member / Non-Member',
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
                        'Txn Id',
                        'Name',
                        'Email',
                        'Paid On',
                        'Total',
                        'Processing Fees',
                        'Total Net Payment',
                    ]

admin_email_accts = [
                        'commodore@sherbornyachtclub.org',
                        'info@sherbornyachtclub.org',
                        'instruction@sherbornyachtclub.org',
                    ]

waterfront_email_accts = [
                        'waterfront@sherbornyachtclub.org',
                        ]

reservation_types = [
                        'SUP',
                        'SUP Windsurfer',
                        'Pedal Boat',
                        'Single Kayak (1 person)',
                        'Double Kayak (2-person)',
                        'Canoe',
                        'Sunfish',
                        '420',
                        'Quest (4-6 people)',
                        'Bic Sailboat (Single)',
                        'Sunfish (Single Adult or 2 Children)',
                        'Pram (beginner)',
                        '420 (advanced)',
                    ]

lesson_types = [
                        'Private Sailing Lesson',
                        'Semi-Private Sailing Lesson',
                        'Private to Semi-Private Add-on',
                        'Sailing Lesson (Private or Semi-Private)',
                        'Intro to Racing Sailing Lessons',
                        'Intro to Watercraft',
                        'First Mates Sailing Lessons',
                        'Supervised Sailing Session',
                        'Sailing Refresher Clinic',
                        'Fall Sailing Class Series',
                        'Intro to Racing Clinic',
                        'Paddle Boarding Lesson',
                        'Mariners Sailing Lessons',
                        'Sailing Race Team',
                        'Paddle Board Lesson',
                        'Yoga SUP Class',
                        'FC Custom',
                        'Windsurfing Clinic',
                ]

race_types = [
                        'SYC Junior Regatta',
                        'Race Series',
                        'SYC Junior Race Day',
                        'Great Burgee Race',
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
        handler.share(email, perm_type='user', role='reader', notify=notify_users)

    logging.debug("Found spreadsheet and returning handler")
    return handler

def append_to_spreadsheet(spreadsheet, worksheet_title, header_row, row_to_add):
    logging.debug("Entering append_to_spreadsheet")

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
        # TOFIX need to sanitize this input
        logging.debug("Couldn't find worksheet %s. Creating" % worksheet_title)
        target_sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1, cols=len(row_to_add))
        target_sheet.append_row(header_row, value_input_option='USER-ENTERED')


    logging.debug("Ready to append_row: %s" % row_to_add)
    start_row = 1
    target_sheet.append_row(row_to_add, value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    target_sheet.columns_auto_resize(0, len(row_to_add))

    return True

def get_appointment_type_by_id(appointment_id):

    appointment_type = ''

    return appointment_type

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

    logging.debug("Ready to write out %s" % formatted_appt)
    # update the google sheet
    try:
        logging.debug("Writing out to mooring spreadsheet: %s" % formatted_appt)
        logging.debug("Spreadsheet info: Spreadsheet Title: %s, Worksheet Title: %s, Header: %s, Row to Append: %s" % (spreadsheet_title, worksheet_title, spreadsheet_header, formatted_appt))
        append_to_spreadsheet(gs, worksheet_title, spreadsheet_header, formatted_appt)
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

    parsed_event = parse_lambda_event(event)
    appointment = get_appointment_by_id(parsed_event['id'])

    if any(reservation in appointment['type'] for reservation in reservation_types):
        logging.debug("Found appointment['type'] in reservation_types: %s" % lesson_types)
        sync_reservation(appointment)
    elif any(lesson in appointment['type'] for lesson in lesson_types):
        logging.debug("Found appointment['type'] in lesson_types: %s" % lesson_types)
    elif any(race in appointment['type'] for race in race_types):
        logging.debug("Found appointment['type'] in race_types: %s" % lesson_types)

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
