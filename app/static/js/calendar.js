function formatDuration(seconds) {
    seconds = Number(seconds);

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}h ${m}min ${s}s`;
    }
    if (m > 0) {
        return `${m}min ${s}s`;
    }
    return `${s}s`;
}


document.addEventListener('DOMContentLoaded', function() {
    let selectedEventId = null;
    const calendar = new FullCalendar.Calendar(
        document.getElementById('calendar'),
        {
            initialView: 'dayGridMonth',
            events: '/api/activities',
            showNonCurrentDates: false,
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek' // boutons de vue
            },
            firstDay: 1,

            datesSet: function(info) {
                selectedEventId = null;
                calendar.refetchEvents();
                Promise.all([
                    fetchHrZones(info.startStr, info.endStr),
                    fetchTotalVolume(info.startStr, info.endStr)
                ])
                .then(([zones, volume]) => {

                    updatePieChart(zones);

                    document.getElementById("total-activities").textContent = volume.total_activities;
                    document.getElementById("total-distance").textContent = volume.total_distance;
                    document.getElementById("total-duration").textContent = volume.total_duration;
                    document.getElementById("total-elevation-gain").textContent = volume.total_elevation_gain;
                });
            },

            eventContent: function(arg) {
                const d = arg.event.extendedProps;

                return {
                    html: `
                        <div>
                            <strong>${arg.event.title}</strong><br>
                            ${(d.distance / 1000).toFixed(1)} km<br>
                            ${formatDuration(d.duration_sec)}
                        </div>
                    `
                };
            },
eventClick: function(info) {

    const clickedId = String(info.event.id);

    // 👉 si on reclique sur le même event = RESET
    if (selectedEventId === clickedId) {

        selectedEventId = null;

        // enlever le highlight visuel
        document.querySelectorAll('.fc-event').forEach(el => {
            el.classList.remove('event-selected');
            el.style.backgroundColor = "";
            el.style.borderColor = "";
        });

        // reload stats période actuelle
        const view = calendar.view;
        fetchHrZones(view.currentStart.toISOString(), view.currentEnd.toISOString())
            .then(updatePieChart);

        return;
    }

    // 👉 sinon sélection normale
    selectedEventId = clickedId;

    // reset visuel
    document.querySelectorAll('.fc-event').forEach(el => {
        el.classList.remove('event-selected');
        el.style.backgroundColor = "";
        el.style.borderColor = "";
    });

    // highlight immédiat
    info.el.classList.add('event-selected');

    // fetch activité
    fetch(`/api/activity-details?id=${clickedId}`)
        .then(res => res.json())
        .then(updatePieChart);
}
        }
    );

    calendar.render();
});
