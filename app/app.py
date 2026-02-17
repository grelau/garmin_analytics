from flask import Flask, render_template, jsonify, request
import boto3
app = Flask(__name__)
from boto3.dynamodb.conditions import Attr, Key, And
from datetime import datetime, timedelta

RUNNING_LABELS = ['running', 'track_running', 'obstacle_run']
CYCLING_LABELS = ['road_biking', 'virtual_ride', 'cycling', 'indoor_cycling']

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ActivitiesTable")

def parse_fc_date(date_str: str):
    dt = datetime.fromisoformat(date_str)
    return dt.replace(tzinfo=None)

def diff_days_months(start_str, end_str, activities, fmt="%Y-%m-%d"):
    if start_str == "":
        start = activities[0][0]
        start = start.split(' ')[0]
        print(start)
        start = datetime.strptime(start, "%Y-%m-%d")
        print(start)
    else:
        start = datetime.strptime(start_str, fmt)
        print(start)
    if end_str == "":
        end = datetime.today()
        print(end)
    else:
        end = datetime.strptime(end_str, fmt)
        print(end)

    delta = end - start
    days = delta.days

    # mois fractionnels (approximation basée sur 30.44 jours = moyenne réelle)
    months = days / 30.44

    return days / 7, months

def build_pr_history(sorted_array):
    pr_history = {}
    best_so_far = {}
#    MAX_TIME = {
#    "5000": 40 * 60,
#    "10000": 80 * 60,
#    "21098": 3 * 3600,
#    "42195": 6 * 3600
#}

    for date, distances in sorted_array:
        for distance, value in distances.items():

            if value is None:
                continue

            #if distance in MAX_TIME and value > MAX_TIME[distance]:
            #    continue

            # initialisation si première fois
            if distance not in best_so_far:
                best_so_far[distance] = value
                pr_history.setdefault(distance, []).append({
                    "date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").isoformat(),
                    "value": int(value)
                })
                continue

            # record si temps plus petit
            if value < best_so_far[distance]:
                best_so_far[distance] = value
                pr_history.setdefault(distance, []).append({
                    "date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").isoformat(),
                    "value": int(value)
                })
    return pr_history

@app.route("/api/performance")
def performances_data():

    sport = request.args.get("sport")
    start = request.args.get("start")
    end = request.args.get("end")
    filter_expr = Attr("activity_best_times").exists()
    date_attr = Attr("startTimeLocal")

    if start and end:
        filter_expr = And(filter_expr, date_attr.between(start, end))
    elif start:
        filter_expr = And(filter_expr, date_attr.gte(start))
    elif end:
        filter_expr = And(filter_expr, date_attr.lte(end))

    response = table.scan(
        FilterExpression=filter_expr
    )

    items = response["Items"]
    print(len(items))
    if sport == 'cycling':
        activities = [(item["startTimeLocal"], item["activity_best_times"]) for item in items if item['activityType']['typeKey'] in CYCLING_LABELS]
    elif sport == 'running':
        activities = [(item["startTimeLocal"], item["activity_best_times"]) for item in items if item['activityType']['typeKey'] in RUNNING_LABELS]
    activities = sorted(activities, key=lambda x: x[0])
    print(len(activities))
    tr_stats = get_training_stats(items, sport)

    days, month = diff_days_months(start, end, activities)
    #si pas de start (l'activité la plus vieille), si pas de end(today)
    print(days, month)

    tr_stats['total_duration'] = tr_stats['total_duration'] / 3600
    tr_stats['total_distance'] = tr_stats['total_distance'] / 1000

    tr_stats['weekly_duration'] = tr_stats['duration'] / 3600 / days
    tr_stats['weekly_distance'] = tr_stats['distance'] / 1000 / days

    tr_stats['monthly_duration'] = tr_stats['duration'] / 3600 / month
    tr_stats['monthly_distance'] = tr_stats['distance'] / 1000 / month

    all_stats = {
        'training': tr_stats,
        'pr': build_pr_history(activities)
    }

    return jsonify(all_stats)

def get_training_stats(items, sport):
    response = table.scan()
    all_items = response["Items"]
    if sport == 'cycling':
        all_activities = [(int(item["duration"]), int(item["distance"])) for item in all_items if item['activityType']['typeKey'] in CYCLING_LABELS]
        activities = [(int(item["duration"]), int(item["distance"])) for item in items if item['activityType']['typeKey'] in CYCLING_LABELS]
    elif sport == 'running':
        all_activities = [(int(item["duration"]), int(item["distance"])) for item in all_items if item['activityType']['typeKey'] in RUNNING_LABELS]
        activities = [(int(item["duration"]), int(item["distance"])) for item in items if item['activityType']['typeKey'] in RUNNING_LABELS]
    tr_stats = {
        'total_distance': 0,
        'total_duration': 0,
        'distance': 0,
        'duration': 0,
    }
    for a in all_activities:
        tr_stats['total_distance'] += a[1]
        tr_stats['total_duration'] += a[0]
    for a in activities:
        tr_stats['distance'] += a[1]
        tr_stats['duration'] += a[0]
    return tr_stats

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/performance")
def performance():
    return render_template("performance.html")


@app.route("/api/activities")
def activities():
    """
    Doit renvoyer les activités au format FullCalendar
    """
    response = table.scan()

    events = []

    for item in response["Items"]:
        events.append({
            "id": item["activity_id"],
            "title": item["activityType"]["typeKey"].capitalize(),
            "start": item["startTimeLocal"].split(" ")[0],  # YYYY-MM-
            "distance": item["distance"],
            "duration_sec": int(item["duration"])
        })

    return jsonify(events)

@app.route("/api/hr-zones")
def hr_zones():
    start = request.args.get("start")
    end = request.args.get("end")

    print(start, end)

    start = parse_fc_date(start)
    end = parse_fc_date(end)

    # rendre end exclusif pour un between inclusif
    end = end - timedelta(seconds=1)

    start = start.strftime("%Y-%m-%d %H:%M:%S")
    end = end.strftime("%Y-%m-%d %H:%M:%S")

    response = table.scan(
        FilterExpression=Attr("startTimeLocal").between(start, end)
    )

    #print(response['Items'][0]['time_in_hr_zone']['z0'])
    zones = {
        "Nodata": 0,
        "z0": 0,
        "z1": 0,
        "z2": 0,
        "z3": 0,
        "z4": 0,
        "z5": 0
    }

    for item in response["Items"]:
        zones["Nodata"] += int(item.get("time_in_hr_zone", {}).get("NoValue", 0))
        zones["z0"] += int(item.get("time_in_hr_zone", {}).get("z0", 0))
        zones["z1"] += int(item.get("time_in_hr_zone", {}).get("z1", 0))
        zones["z2"] += int(item.get("time_in_hr_zone", {}).get("z2", 0))
        zones["z3"] += int(item.get("time_in_hr_zone", {}).get("z3", 0))
        zones["z4"] += int(item.get("time_in_hr_zone", {}).get("z4", 0))
        zones["z5"] += int(item.get("time_in_hr_zone", {}).get("z5", 0))

    return jsonify(zones)

@app.route("/api/activity-details")
def activity_details():
    activity_id = request.args.get("id")
    response = table.query(
        KeyConditionExpression=Key("activity_id").eq(int(activity_id))
    )
    activity = response['Items'][0]
    zones = {
        "Nodata": int(activity.get("time_in_hr_zone", {}).get("NoValue", 0)),
        "z0": int(activity.get("time_in_hr_zone", {}).get("z0", 0)),
        "z1": int(activity.get("time_in_hr_zone", {}).get("z1", 0)),
        "z2": int(activity.get("time_in_hr_zone", {}).get("z2", 0)),
        "z3": int(activity.get("time_in_hr_zone", {}).get("z3", 0)),
        "z4": int(activity.get("time_in_hr_zone", {}).get("z4", 0)),
        "z5": int(activity.get("time_in_hr_zone", {}).get("z5", 0))
    }

    return jsonify(zones)

def seconds_to_hours_minutes(seconds: int) -> str:
    if not seconds:
        return "0 h 0 min"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return f"{hours} h {minutes} min"


@app.route("/api/total-volume")
def total_volume():
    start = request.args.get("start")
    end = request.args.get("end")

    print(start, end)

    start = parse_fc_date(start)
    end = parse_fc_date(end)

    # rendre end exclusif pour un between inclusif
    end = end - timedelta(seconds=1)

    start = start.strftime("%Y-%m-%d %H:%M:%S")
    end = end.strftime("%Y-%m-%d %H:%M:%S")

    response = table.scan(
        FilterExpression=Attr("startTimeLocal").between(start, end)
    )

    volume = {
        "total_activities": 0,
        "total_distance": 0,
        "total_duration": 0,
        "total_elevation_gain": 0,
    }

    for item in response["Items"]:
        volume["total_activities"] += 1
        volume["total_distance"] += int(item.get("distance", 0))
        volume["total_duration"] += int(item.get("duration", 0))
        volume["total_elevation_gain"] += int(item.get("elevationGain") or 0)

    volume['total_distance'] = round(volume['total_distance'] / 1000, 2)
    volume['total_duration'] = seconds_to_hours_minutes(volume['total_duration'])
    
    print(volume)

    return jsonify(volume)

if __name__ == "__main__":
    app.run(debug=True)