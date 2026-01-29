from flask import Flask, render_template, jsonify, request
import boto3
app = Flask(__name__)
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ActivitiesTable")

@app.route("/")
def home():
    return render_template("home.html")


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
            "duration_min": int(item["duration"] / 60)
        })

    return jsonify(events)

@app.route("/api/hr-zones")
def hr_zones():
    start = request.args.get("start")
    end = request.args.get("end")

    print(start, end)

    response = table.scan(
        FilterExpression=Attr("startTimeLocal").between(start, end)
    )

    print(response['Items'][0]['time_in_hr_zone']['z0'])
    zones = {
        "z1": 0,
        "z2": 0,
        "z3": 0,
        "z4": 0,
        "z5": 0
    }

    for item in response["Items"]:
        zones["z1"] += int(item.get("time_in_hr_zone", {}).get("z1", 0))
        zones["z2"] += int(item.get("time_in_hr_zone", {}).get("z2", 0))
        zones["z3"] += int(item.get("time_in_hr_zone", {}).get("z3", 0))
        zones["z4"] += int(item.get("time_in_hr_zone", {}).get("z4", 0))
        zones["z5"] += int(item.get("time_in_hr_zone", {}).get("z5", 0))

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
