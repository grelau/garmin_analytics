import boto3
from boto3.dynamodb.conditions import Attr
import json

def get_activity_pr(activity: dict, target_distance: int, db_duration: int, activity_distance: int) -> int:
    try:
        for descriptor in activity["metricDescriptors"]:  
            if descriptor["key"] == "sumDistance":
                distance = descriptor["metricsIndex"]
            if descriptor["key"] == "sumElapsedDuration":
                time = descriptor["metricsIndex"]
    except TypeError: #fallback
        print('fallback call')
        return db_duration * target_distance / activity_distance

    metrics = activity['activityDetailMetrics']

    best_time = None
    i = 0

    for j in range(len(metrics)):
        while metrics[j]['metrics'][distance] - metrics[i]['metrics'][distance] >= target_distance:
            duration = metrics[j]['metrics'][time] - metrics[i]['metrics'][time]

            if best_time is None or duration < best_time:
                best_time = duration

            i += 1
    
    return best_time

def add_pr_to_table(ACTIVITY_LABELS: list, DISTANCES: list) -> None:
    response = table.scan(
        FilterExpression=Attr("activity_best_times").not_exists()
    )

    items = response["Items"]
    print(len(items))
    activities = [(item["activity_id"], item['activityType']['typeKey'], item['distance'], item['duration']) for item in items]

    s3 = boto3.client("s3")
    bucket_name = "garmin-activity-bucket"

    for id, label, activity_distance, db_duration in activities:
        int_id = int(id)
        if label in ACTIVITY_LABELS:
            print(f'processing {int_id}')
            response = s3.get_object(Bucket=bucket_name, Key= f"{int_id}.json")
            content = response["Body"].read().decode("utf-8")
            activity = json.loads(content)
            prs = {
            }
            for distance in DISTANCES:
                if activity_distance >= distance:
                    pr = get_activity_pr(activity, distance, db_duration, activity_distance)
                    if pr == None:
                        print(f'on est sur un cas border: {int_id}')
                        pr = db_duration
                    prs[str(distance)] = int(pr)
                else: 
                    prs[str(distance)] = None
            print(prs)
            table.update_item(
                Key={"activity_id": int_id},
                UpdateExpression="SET activity_best_times = :prs",
                ExpressionAttributeValues={
                    ":prs": prs
                }
            )
            print(f'table updated for {int_id}')
        else:
            print(f'{int_id} not in {ACTIVITY_LABELS} label, label: {label}')



dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
table = dynamodb.Table("ActivitiesTable")

RUNNING_LABELS = ['running', 'track_running', 'obstacle_run']
RUNNING_DISTANCES = [5000, 10000, 12000, 14000, 15000, 16000, 18000, 20000, 21098, 25000, 30000, 35000, 40000, 42195]
CYCLING_LABELS = ['road_biking', 'virtual_ride', 'cycling', 'indoor_cycling']
CYCLING_DISTANCES = [20000, 30000, 40000, 50000, 75000, 100000, 150000, 200000, 250000]
SWIMMING_LABELS = ['lap_swimming', 'swimming']
SWIMMING_DISTANCES = [50,100,200,500,750,1000,1500,2000]

#add_pr_to_table(SWIMMING_LABELS, SWIMMING_DISTANCES)
add_pr_to_table(CYCLING_LABELS, CYCLING_DISTANCES)
    