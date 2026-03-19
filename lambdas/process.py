import json
import logging
import boto3

from utils.dynamo_helpers import add_item_to_dynamo_db, create_item

def request(event, context):

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for record in event["Records"]:

        message = json.loads(record["body"])

        user_id = message["user_id"]
        activity = message["activity"]
        user_zones = message["user_zones"]

        activity_id = activity['activityId']

        s3 = boto3.client("s3")
        bucket_name = "garmin-activity-bucket"

        response = s3.get_object(Bucket=bucket_name, Key=f"{user_id}/{activity_id}.json")
        content = response["Body"].read().decode("utf-8")
        activity_details = json.loads(content)


        logger.info(f"Processing activity: {activity_id}")


        item = create_item(user_id, activity, user_zones, activity_details)
        add_item_to_dynamo_db(item)
