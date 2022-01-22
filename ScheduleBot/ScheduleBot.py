# importing the required libraries
import gspread
import pandas as pd
import json
import numpy as np
import csv
import re
import time
from oauth2client.service_account import ServiceAccountCredentials
from importlib import reload

gspread = reload(gspread)
json = reload(json)
pd = reload(pd)
csv = reload(csv)
re = reload(re)

# create dictionary for 2D arrays
user_dict = dict()

# CSV Import
with open('data.csv', mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    line_count = 0
    for row in csv_reader:
        if line_count == 0:
            line_count += 1
        # print(f'\t{row["First Name"]} {row["Last Name"]} with email {row["Email"]}, signed up for class, {row["Type"]}.')

        # really bad string prep
        type_fixed = re.sub(':', '', row["Type"])
        # type_fixed = re.sub(r'\s+$', ' ', type_fixed)

        array_key = f'\t{row["First Name"]}{row["Last Name"]}{row["Email"]}{type_fixed}'

        # fill array here
        if type_fixed not in user_dict.keys():
            user_dict[type_fixed] = np.empty([0,8])
            #could probably be a function to add a user
            insert_array = np.array([array_key, row["First Name"], row["Last Name"], row["Phone"], row["Email"], row["Swimming Ability"], 'unsure', row["Amount Paid Online"]])
            user_dict[type_fixed] = np.append(user_dict[type_fixed], [insert_array], axis=0)
            line_count += 1
            continue

        skip_bool = False
        for x in user_dict[type_fixed]:
            if x[0] == array_key:
                skip_bool = True
                break

        if skip_bool == True:
            continue

        insert_array = np.array([array_key, row["First Name"], row["Last Name"], row["Phone"], row["Email"], row["Swimming Ability"], 'unsure', row["Amount Paid Online"]])
        user_dict[type_fixed] = np.append(user_dict[type_fixed], [insert_array], axis=0)

        line_count += 1
    print(f'Processed {line_count} lines.')

if len(user_dict) == 0:
    print('quit: no new users')
    quit()

# define the scope
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)

# authorize the clientsheet 
client = gspread.authorize(creds)

# get the instance of the Spreadsheet
spreadsheet = client.open('SYC Testing')

# create an array of sheet names, this will be used as a key to compare against the inputs
sheet_array = spreadsheet.worksheets()
sheet_names = np.empty([0])
for sheet in sheet_array:
    sheet_names = np.append(sheet_names, [sheet.title], axis=0)

# check here if a Total Revenue sheet exists
found = False 
for x in sheet_names:
    if x == 'Total Revenue':
        found = True
        break
if found == False:
    # this could be a function
    sheet_create = spreadsheet.add_worksheet("Total Revenue", 1, 2, index=0)
    sheet_names = np.insert(sheet_names, 0, ["Total Revenue"])
    sheet_create.append_row(['Class', 'Revenue'], value_input_option='USER-ENTERED', table_range='A1:B1')
    sheet_create.append_row(['Total', '=SUM(INDIRECT(ADDRESS(1,COLUMN())&":"&ADDRESS(ROW()-1,COLUMN())))'], value_input_option='USER-ENTERED', table_range='A1:B1')
    # update sheet_array
    sheet_array = spreadsheet.worksheets()

# check keys 
for key in user_dict:
    skip_bool = False
    for x in sheet_names:
        if key == x:
            skip_bool = True
            break
    if skip_bool == True:
        continue
    # if the sheet does not exist, we need to create it
    else:
        sheet_create = spreadsheet.add_worksheet(key, 1, 8, index=None)
        sheet_names = np.append(sheet_names, [key], axis=0)
        sheet_create.append_row(['ID', 'First Name', 'Last Name', 'Phone', 'Email', 'Swim Ability', 'Member or Non Member', 'Paid'], value_input_option='USER-ENTERED', table_range='A1:H1')
        # update Total Revenue sheet with new sheet
        count = 0
        for y in sheet_names:
            if y == "Total Revenue":
                break
            count += 1
        sheet_revenue = spreadsheet.get_worksheet(count)
        insert_row = sheet_revenue.row_count
        time.sleep(10) # temporary?
        sheet_revenue.insert_row([key, "=SUM('{}'!H:H)".format(key)], index=insert_row, value_input_option='USER-ENTERED')
        sheet_revenue.columns_auto_resize(0, 1)
        
# update sheet_array since we've potentially added sheets
sheet_array = spreadsheet.worksheets()

for key in user_dict:
    count = 0
    for x in sheet_names:
        if x == key:
            break
        count += 1
    sheet_instance = spreadsheet.get_worksheet(count)
    next_id = sheet_instance.row_count
    start_row = next_id + 1
    count = 0
    for x in user_dict[key]:
        # write new line
        user_dict[key][count][0] = next_id
        next_id += 1
        count += 1
    time.sleep(10) # temporary?
    sheet_instance.append_rows(user_dict[key].tolist(), value_input_option='USER-ENTERED', table_range='A{}'.format(start_row))
    sheet_instance.columns_auto_resize(0, 7)
print('end')