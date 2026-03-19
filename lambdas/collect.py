import os
import logging
import json
import boto3
import garminconnect
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from utils.dynamo_helpers import save_activity_json_to_s3

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    
def process_activity(garmin, sqs, QUEUE_URL: str ,activity: dict, user_id: int, user_zones: dict) -> None:

    activity_id = activity['activityId']

    activity_details = garmin.get_activity_details(activity_id)

    save_activity_json_to_s3(user_id, activity_id, activity_details)

    message = {
        "user_id": user_id,
        "activity": activity,
        "user_zones": user_zones
    }

    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message, default=convert_decimal)
    )

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

    user_zones = {
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
    s3_ids = [int(object['Key'].split('/')[1].split('.json')[0]) for object in s3_files]
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

    sqs = boto3.client("sqs")

    QUEUE_URL = os.environ["SQS_URL"]

    all_activities = [activity for activity in all_activities if activity['activityId'] in missing_ids]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for activity in all_activities:
            executor.submit(
                process_activity,
                garmin,
                sqs,
                QUEUE_URL,
                activity,
                user_id,
                user_zones
            )



    return {
        'statusCode': 200,
        'body': 'Daily ingestion done!'
    }