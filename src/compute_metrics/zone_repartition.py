import json

with open("data/running/21453616324.json", "r") as f:
    activity = json.load(f)


##finding the HR index
hr_index = None
for descriptor in activity["metricDescriptors"]:
    if descriptor["key"] == "directHeartRate":
        hr_index = descriptor["metricsIndex"]
    if descriptor["key"] == "sumElapsedDuration":
        time = descriptor["metricsIndex"]
if hr_index is None:
    raise ValueError("Heart rate metric not found")
if time is None:
    raise ValueError("Heart rate metric not found")

print(hr_index, time)

#summing HR zones time
metrics = activity['activityDetailMetrics']

z1, z2, z3, z4, z5 = 0,126,146,166,185

z1_count, z2_count, z3_count, z4_count, z5_count = 0,0,0,0,0
for i in range(1, len(metrics)):
    current = metrics[i]
    previous = metrics[i - 1]

    HR = current['metrics'][hr_index]

    delta_t = current['metrics'][time] - previous['metrics'][time]

    if HR > z5:
        z5_count += delta_t
    elif HR > z4:
        z4_count += delta_t
    elif HR > z3:
        z3_count += delta_t
    elif HR > z2:
        z2_count += delta_t
    else:
        z1_count += delta_t


print(z1_count, z2_count, z3_count, z4_count, z5_count)


