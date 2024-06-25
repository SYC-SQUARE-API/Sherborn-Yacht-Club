"""
Author: Brent Holden
Description: AWS Lambda function to insert order data into PostgreSQL database.
"""

import json
import os
import psycopg2
from psycopg2 import sql

def handler(event, context):
    # Get database credentials from environment variables
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASS")
    db_server = os.environ.get("DB_SERVER")

    # Construct the connection string
    db_conn_string = f'postgresql://{db_user}:{db_password}@{db_server}.us-west-2.retooldb.com/retool?sslmode=require'

    # Parse the JSON payload
    try:
        payload = json.loads(event['body'])
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid JSON: {str(e)}")
        }
    
    # Connect to the database
    try:
        conn = psycopg2.connect(db_conn_string)
        cursor = conn.cursor()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Database connection error: {str(e)}")
        }
    
    # Insert data into the table
    try:
        for line_item in payload['lineItems']:
            # Handle missing variantOptions
            variant_options = json.dumps(line_item['variantOptions']) if 'variantOptions' in line_item else None
            
            query = sql.SQL("""
                INSERT INTO syc_orders (
                    id, order_number, created_on, modified_on, channel, testmode, customer_email,
                    billing_first_name, billing_last_name, billing_address1, billing_address2,
                    billing_city, billing_state, billing_country_code, billing_postal_code, billing_phone,
                    fulfillment_status, line_item_id, variant_id, variant_options, sku, product_id, product_name,
                    quantity, unit_price_paid, image_url, line_item_type, customizations, subtotal, shipping_total,
                    discount_total, tax_total, refunded_total, grand_total, channel_name, external_order_reference,
                    fulfilled_on, price_tax_interpretation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """)
            values = (
                line_item['id'], payload['orderNumber'], payload['createdOn'], payload['modifiedOn'], payload['channel'], payload['testmode'],
                payload['customerEmail'], payload['billingAddress']['firstName'], payload['billingAddress']['lastName'],
                payload['billingAddress']['address1'], payload['billingAddress']['address2'], payload['billingAddress']['city'],
                payload['billingAddress']['state'], payload['billingAddress']['countryCode'], payload['billingAddress']['postalCode'],
                payload['billingAddress']['phone'], payload['fulfillmentStatus'], line_item['id'], line_item['variantId'],
                variant_options, line_item['sku'], line_item['productId'], line_item['productName'], line_item['quantity'],
                line_item['unitPricePaid']['value'], line_item['imageUrl'], line_item['lineItemType'],
                json.dumps(line_item['customizations']), payload['subtotal']['value'], payload['shippingTotal']['value'],
                payload['discountTotal']['value'], payload['taxTotal']['value'], payload['refundedTotal']['value'],
                payload['grandTotal']['value'], payload['channelName'], payload['externalOrderReference'], payload['fulfilledOn'],
                payload['priceTaxInterpretation']
            )
            #print(f"Executing query with values: {values}")  # Debug log to show the values being inserted
            cursor.execute(query, values)
            print("Data inserted successfully")
        conn.commit()
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"Error inserting data: {str(e)}")  # Debug log to show the error
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error inserting data: {str(e)}")
        }
    
    # Close the database connection
    cursor.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data inserted successfully!')
    }

