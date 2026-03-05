import os
import logging
import json
import boto3
import garminconnect

from utils.dynamo_helpers import convert_to_decimal, chunks
from utils.extra_metrics import get_zones_distribution, get_activity_records

def request(event, context):

    user_id = 1

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')

    dynamodb = boto3.resource('dynamodb')
    activities_db = dynamodb.Table('Activities')
    users_db = dynamodb.Table('Users')

    response = users_db.get_item(Key={"user_id": user_id})

    user_row = response.get("Item")

    users_zones = {
        "cycling_hr_zones": user_row.get("cycling_hr_zones", {}),
        "running_hr_zones": user_row.get("running_hr_zones", {}),
        "swimming_hr_zones": user_row.get("swimming_hr_zones", {})
    }

    s3 = boto3.client('s3')
    bucket_name = 'garmin-activity-bucket'

    #create ids list and checks if s3 and dynamo ids matches
    activities_db_response = activities_db.scan() #FILTRER PAR USER_ID
    activities_dynamo_data = activities_db_response.get('Items', [])
    dynamo_ids = [int(item['activity_id']) for item in activities_dynamo_data]
    dynamo_ids.sort()

    s3_response = s3.list_objects_v2(Bucket=bucket_name, Prefix=f"{user_id}/") #FILTRER PAR USER_id, retourne max 1000 objets gérer la pagination plus tard
    s3_files = s3_response.get('Contents', [])
    s3_ids = [int(object['Key'].split('.json')[0]) for object in s3_files]
    s3_ids.sort()

    if dynamo_ids != s3_ids:
        raise ValueError("les ids contenus dans dynamo et S3 devraient être systématiquement identiques")


    garmin = garminconnect.Garmin(email, password)
    garmin.login()
    logger.info("connected to API")
    
    all_activities = garmin.get_activities(0,10000) #peut etre un pb mais c'est le max qu'on peut fournir en param
    logger.info("Garmin connect responding")
    
    garmin_ids = [activity['activityId'] for activity in all_activities]
    missing_ids = list(set(garmin_ids) - set(dynamo_ids))
    logger.info(str(len(missing_ids)) + " activities to add")
    
    items = [
    {
        'user_id': user_id,
        'activity_id': activity['activityId'],
        'startTimeLocal': activity['startTimeLocal'],
        'activityType': activity['activityType']['typeKey'],
        'distance': convert_to_decimal(activity.get('distance')),
        'elapsedDuration': convert_to_decimal(activity.get('elapsedDuration')),
        'duration': convert_to_decimal(activity.get('duration')),
        'elevationGain': convert_to_decimal(activity.get('elevationGain')),
        'elevationLoss': convert_to_decimal(activity.get('elevationLoss')),
        'averageSpeed': convert_to_decimal(activity.get('averageSpeed')),
        'averageHR': convert_to_decimal(activity.get('averageHR')),
        'maxHR': convert_to_decimal(activity.get('maxHR')),
        'aerobicTrainingEffect': convert_to_decimal(activity.get('aerobicTrainingEffect')),
        'anaerobicTrainingEffect': convert_to_decimal(activity.get('anaerobicTrainingEffect')),
        'time_in_hr_zone': get_zones_distribution(garmin, activity['activityId'], activity['activityType']['typeKey'],
                                                 users_zones, convert_to_decimal(activity.get('duration'))),
        'activity_best_times': get_activity_records(garmin, activity['activityId'], activity['activityType']['typeKey'], 
                                                    convert_to_decimal(activity.get('duration')), convert_to_decimal(activity.get('distance'))) 
    }
    for activity in all_activities
    if activity['activityId'] in missing_ids
]
    
    for batch in chunks(items, 25):
        with activities_db.batch_writer() as batch_writer:
            for item in batch:
                batch_writer.put_item(Item=item)
    logger.info("Items written in Dynamo")

    for item in items:
        response = garmin.get_activity_details(item['activity_id'])
        s3.put_object(
            Bucket=bucket_name,
            Key=f"{user_id}/{item['activity_id']}.json",
            Body=json.dumps(response, indent=4))

    logger.info("Jsons written to S3")

    
    return {
        'statusCode': 200,
        'body': 'Daily ingestion done!'
    }