import os
import logging
import json
import boto3
import garminconnect
from datetime import datetime
from decimal import Decimal, InvalidOperation

def convert_to_decimal(value):
    if value is None:
        return None
    try:
        decimal_value = Decimal(value)
        return decimal_value.quantize(Decimal('1.000'))
    except (InvalidOperation, ValueError) as e:
        print(f"Error converting value '{value}' to Decimal: {e}")
        return None
    
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def request(event, context):

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ActivitiesTable')

    s3 = boto3.client('s3')
    bucket_name = 'garmin-activity-bucket'

    #create ids list and checks if s3 and dynamo ids matches
    dynamo_response = table.scan()
    all_dynamo_data = dynamo_response.get('Items', [])
    dynamo_ids = [int(item['activity_id']) for item in all_dynamo_data]
    dynamo_ids.sort()

    s3_response = s3.list_objects_v2(Bucket=bucket_name)
    s3_files = s3_response.get('Contents', [])
    s3_ids = [int(object['Key'].split('.json')[0]) for object in s3_files]
    s3_ids.sort()

    if dynamo_ids != s3_ids:
        raise ValueError("les ids contenus dans dynamo et S3 devraient être systématiquement identiques")


    garmin = garminconnect.Garmin(email, password)
    garmin.login()
    logger.info("connected to API")
    
    all_activities = garmin.get_activities(0,10000)
    logger.info("Garmin connect responding")
    
    garmin_ids = [activity['activityId'] for activity in all_activities]
    missing_ids = list(set(garmin_ids) - set(dynamo_ids))
    logger.info(str(len(missing_ids)) + " activities to add")
    
    items = [
    {
        'activity_id': activity['activityId'],
        'startTimeLocal': activity['startTimeLocal'],
        'activityType': activity['activityType'],
        'distance': convert_to_decimal(activity.get('distance')),
        'elapsedDuration': convert_to_decimal(activity.get('elapsedDuration')),
        'duration': convert_to_decimal(activity.get('duration')),
        'elevationGain': convert_to_decimal(activity.get('elevationGain')),
        'elevationLoss': convert_to_decimal(activity.get('elevationLoss')),
        'averageSpeed': convert_to_decimal(activity.get('averageSpeed')),
        'averageHR': convert_to_decimal(activity.get('averageHR')),
        'maxHR': convert_to_decimal(activity.get('maxHR')),
        'aerobicTrainingEffect': convert_to_decimal(activity.get('aerobicTrainingEffect')),
        'anaerobicTrainingEffect': convert_to_decimal(activity.get('anaerobicTrainingEffect'))
    }
    for activity in all_activities
    if activity['activityId'] in missing_ids
]
    
    for batch in chunks(items, 25):
        with table.batch_writer() as batch_writer:
            for item in batch:
                batch_writer.put_item(Item=item)
    logger.info("Items written in Dynamo")

    for item in items:
        response = garmin.get_activity_details(item['activity_id'])
        s3.put_object(
            Bucket=bucket_name,
            Key=f"{item['activity_id']}.json",
            Body=json.dumps(response, indent=4))

    logger.info("Jsons written to S3")

    
    return {
        'statusCode': 200,
        'body': 'Daily ingestion done!'
    }