import boto3
from boto3.dynamodb.conditions import Attr

import json

RUNNING_HR_ZONES = {
    'z1': 118,
    'z2': 126,
    'z3': 146,
    'z4': 166,
    'z5': 185
}

CYCLING_HR_ZONES = {
    'z1': 121,
    'z2': 140,
    'z3': 159,
    'z4': 172,
    'z5': 179
}

CYCLING_LABELS = ['road_biking', 'virtual_ride', 'cycling', 'indoor_cycling']
RUNNING_LABELS = ['running', 'walking', 'track_running', 'obstacle_run']

dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
table = dynamodb.Table("ActivitiesTable")

response = table.scan(
    FilterExpression=Attr("averageHR").ne(None)
)

items = response["Items"]
activities = [(item["activity_id"], item['activityType']['typeKey']) for item in items]

s3 = boto3.client("s3")
bucket_name = "garmin-activity-bucket"

def get_zone_distribution(activity, HR_ZONE_MAPPING):
    
    for descriptor in activity["metricDescriptors"]:
        if descriptor["key"] == "directHeartRate":
            hr_index = descriptor["metricsIndex"]
        if descriptor["key"] == "sumElapsedDuration":
            time = descriptor["metricsIndex"]
    if hr_index is None:
        raise ValueError("Heart rate metric not found")
    if time is None:
        raise ValueError("SumElapsedTime metric not found")

    metrics = activity['activityDetailMetrics']

    z0_count, z1_count, z2_count, z3_count, z4_count, z5_count, No_value_count = 0,0,0,0,0,0,0
    for i in range(1, len(metrics)):
        current = metrics[i]
        previous = metrics[i - 1]

        HR = current['metrics'][hr_index]
        if HR is None:
            HR = previous['metrics'][hr_index]

        delta_t = current['metrics'][time] - previous['metrics'][time]
        try:
            if HR is None:
                No_value_count += 1
            elif HR > HR_ZONE_MAPPING['z5']:
                z5_count += delta_t
            elif HR > HR_ZONE_MAPPING['z4']:
                z4_count += delta_t
            elif HR > HR_ZONE_MAPPING['z3']:
                z3_count += delta_t
            elif HR > HR_ZONE_MAPPING['z2']:
                z2_count += delta_t
            elif HR > HR_ZONE_MAPPING['z1']:
                z1_count += delta_t
            else:
                z0_count += delta_t
        except:
            raise ValueError(f'{HR}, {current}, {current['metrics'][time]}')
    return {
        'z0': int(z0_count),
        'z1': int(z1_count),
        'z2': int(z2_count),
        'z3': int(z3_count),
        'z4': int(z4_count),
        'z5': int(z5_count),
        'NoValue': int(No_value_count)
    }

for id, label in activities:
    int_id = int(id)
    response = s3.get_object(Bucket=bucket_name, Key= f"{int_id}.json")
    content = response["Body"].read().decode("utf-8")
    activity = json.loads(content)
    print(f'processing {int_id}')
    if label in CYCLING_LABELS:
        zone_distribution = get_zone_distribution(activity, CYCLING_HR_ZONES)
    else:
        zone_distribution = get_zone_distribution(activity, RUNNING_HR_ZONES)

    table.update_item(
        Key={"activity_id": id},
        UpdateExpression="SET time_in_hr_zone = :zones",
        ExpressionAttributeValues={
            ":zones": zone_distribution
        }
    )
    print(f"update done for {id}, {label}, {zone_distribution}")

