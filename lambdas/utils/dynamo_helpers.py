from decimal import Decimal, InvalidOperation
import boto3
import logging
import json

from utils.extra_metrics import get_zones_distribution, get_activity_records

logger = logging.getLogger(__name__)

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

def add_item_to_dynamo_db(item: dict) -> None:
    dynamodb = boto3.resource('dynamodb')
    activities_db = dynamodb.Table('Activities')
    activities_db.put_item(Item=item)
    logger.info('item written in activities db')

def create_item(user_id: int, activity: dict, user_zones: dict, activity_details: dict) -> dict:
    """Crée l'item pret a etre ecrit dans dynamo"""
    item = {
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
        'time_in_hr_zone': get_zones_distribution(activity_details, activity['activityId'], activity['activityType']['typeKey'],
                                                 user_zones, convert_to_decimal(activity.get('duration'))),
        'activity_best_times': get_activity_records(activity_details, activity['activityId'], activity['activityType']['typeKey'], 
                                                    convert_to_decimal(activity.get('duration')), convert_to_decimal(activity.get('distance'))) 
        }
    return item

def save_activity_json_to_s3(user_id: int, activity_id: int, activity_details: dict) -> None:
    s3 = boto3.client('s3')
    bucket_name = 'garmin-activity-bucket'
    s3.put_object(
        Bucket=bucket_name,
        Key=f"{user_id}/{activity_id}.json",
        Body=json.dumps(activity_details, indent=4)
    )