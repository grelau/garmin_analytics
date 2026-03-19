import logging

logger = logging.getLogger(__name__)

CYCLING_LABELS = ['road_biking', 'virtual_ride', 'cycling', 'indoor_cycling']
#RUNNING_LABELS = ['running', 'walking', 'track_running', 'obstacle_run', 'indoor_climbing', 'rock_climbing'
#                  'strength_training', 'tennis_v2', 'cross_country_skiing_ws', 'soccer', 'basketball',
#                  'multi_sport']
SWIMMING_LABELS = ['lap_swimming', 'swimming']

RUNNING_LABELS = ['running', 'track_running', 'obstacle_run']
RUNNING_DISTANCES = [5000, 10000, 12000, 14000, 15000, 16000, 18000, 20000, 21098, 25000, 30000, 35000, 40000, 42195]
CYCLING_DISTANCES = [20000, 30000, 40000, 50000, 75000, 100000, 150000, 200000, 250000]
SWIMMING_DISTANCES = [50,100,200,500,750,1000,1500,2000]


def get_activity_pr(activity: dict, target_distance: int, activity_duration: int, activity_distance: int) -> int:
    """retourne le meilleur temps en sec sur l'ensemble de l'activité 
    pour une distance donnée"""
    try:
        for descriptor in activity["metricDescriptors"]:  
            if descriptor["key"] == "sumDistance":
                distance = descriptor["metricsIndex"]
            if descriptor["key"] == "sumElapsedDuration":
                time = descriptor["metricsIndex"]
    except TypeError: #fallback
        logger.info('fallback call')
        return activity_duration * target_distance / activity_distance

    metrics = activity['activityDetailMetrics']

    best_time = None
    i = 0

    for j in range(len(metrics)):
        if metrics[j]['metrics'][distance] is None:
            continue
        while metrics[i]['metrics'][distance] is None:
            i+=1
        while metrics[j]['metrics'][distance] - metrics[i]['metrics'][distance] >= target_distance:
            duration = metrics[j]['metrics'][time] - metrics[i]['metrics'][time]

            if best_time is None or duration < best_time:
                best_time = duration

            i += 1
    
    return best_time


def get_activity_records(activity, activity_id, label, activity_duration, activity_distance) -> dict:
    """retourne un dict de records par distance adapté au type d'activité"""
    logger.info(f'computing PRs for activity: {activity_id}')
    if label in CYCLING_LABELS:
        DISTANCES = CYCLING_DISTANCES
    elif label in SWIMMING_LABELS:
        DISTANCES = SWIMMING_DISTANCES
    elif label in RUNNING_LABELS:
        DISTANCES = RUNNING_DISTANCES
    else:
        logger.info(f'{activity_id} not in cycling, running or swimming label, label: {label}, not computing PRs')
        return None
    
    int_id = int(activity_id)
    prs = {}
    for distance in DISTANCES:
        if activity_distance >= distance:
            pr = get_activity_pr(activity, distance, activity_duration, activity_distance)
            if pr == None:
                print(f'on est sur un cas border: {int_id}')
                pr = activity_duration
            prs[str(distance)] = int(pr)
        else: 
            prs[str(distance)] = None
    logger.info(f'Pr computed for: {int_id}; result: {prs}')
    return prs


def get_zones_distribution(activity: dict, activity_id: int, label: str, HR_ZONE_MAPPING: dict, duration: float) -> dict:
    """renvoie un dictionnaire de temps passé dans chaque zone cardiaque
    pour un json d'une activité donnée"""
    logger.info(f'computing zones for activity: {activity_id}')
    fall_back_dict = {
        'z0': 0,
        'z1': 0,
        'z2': 0,
        'z3': 0,
        'z4': 0,
        'z5': 0,
        'NoValue': int(duration)
    }
    try:
        hr_index = None
        time = None
        for descriptor in activity["metricDescriptors"]:
            if descriptor["key"] == "directHeartRate":
                hr_index = descriptor["metricsIndex"]
            if descriptor["key"] == "sumElapsedDuration":
                time = descriptor["metricsIndex"]
        if hr_index == None or time == None:
            logger.info("no HR or no duration")
            return fall_back_dict
    except TypeError:
        logger.info(f"no json metrics for {activity_id}")
        return fall_back_dict

    metrics = activity['activityDetailMetrics']

    if label in CYCLING_LABELS:
        HR_ZONE_MAPPING = HR_ZONE_MAPPING['cycling_hr_zones']
    elif label in SWIMMING_LABELS:
        HR_ZONE_MAPPING = HR_ZONE_MAPPING['swimming_hr_zones']
    else:
        HR_ZONE_MAPPING = HR_ZONE_MAPPING['running_hr_zones']

    z0_count, z1_count, z2_count, z3_count, z4_count, z5_count, No_value_count = 0,0,0,0,0,0,0
    for i in range(1, len(metrics)):
        current = metrics[i]
        previous = metrics[i - 1]

        HR = current['metrics'][hr_index]

        delta_t = current['metrics'][time] - previous['metrics'][time]
        try:
            if HR is None:
                No_value_count += 1 #un peu inexact
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