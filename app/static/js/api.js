function fetchHrZones(start, end) {
    return fetch(`/api/hr-zones?start=${start}&end=${end}`)
        .then(res => res.json());
}

function fetchTotalVolume(start, end) {
    return fetch(`/api/total-volume?start=${start}&end=${end}`)
        .then(res => res.json());
}
