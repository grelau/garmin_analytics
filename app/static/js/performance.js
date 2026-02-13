/*
document.addEventListener("DOMContentLoaded", function () {

    fetch("/api/performance")
        .then(res => res.json())
        .then(data => initChart(data));

});

function initChart(data) {

    const datasets = [];

    const distanceMap = {
        "5000": "5k",
        "10000": "10k",
        "21098": "21k",
        "42195": "42k"
    };

    const colors = {
        "5k": "#4caf50",
        "10k": "#2196f3",
        "21k": "#ff9800",
        "42k": "#f44336"
    };

    Object.keys(distanceMap).forEach(distance => {

        if (!data[distance]) return; // skip si pas présent

        const label = distanceMap[distance];

        const points = data[distance].map(entry => ({
            x: entry.date,
            y: entry.value / 60
        }));

        datasets.push({
            label: label,
            data: points,
            borderColor: colors[label] || "#999",
            tension: 0.2
        });
    });

const ctx = document.getElementById("prChart");

const chart = new Chart(ctx, {
    type: "line",
    data: { datasets: datasets },
    options: {
        responsive: true,

        interaction: {
            mode: "nearest",
            intersect: false
        },

        plugins: {
            legend: {
                onHover: (event) => {
                    event.native.target.style.cursor = 'pointer';
                },
                onLeave: (event) => {
                    event.native.target.style.cursor = 'default';
                },
                onClick: function (e, legendItem, legend) {
                    const chart = legend.chart;
                    const index = legendItem.datasetIndex;

                    // combien de datasets visibles ?
                    const visibleCount = chart.data.datasets.filter(ds => !ds.hidden).length;

                    if (visibleCount === 1) {
                        // 🔁 Si déjà focus → on réaffiche tout
                        chart.data.datasets.forEach(ds => ds.hidden = false);
                    } else {
                        // 🔥 Sinon on cache tout sauf celui cliqué
                        chart.data.datasets.forEach((ds, i) => {
                            ds.hidden = i !== index;
                        });
                    }

                    chart.update();
                }
            }
        },

        scales: {
            x: {
                type: "time",
                time: {
                    unit: "month"
                }
            },
            y: {
                reverse: false,
                title: {
                    display: true,
                    text: "Temps (min)"
                }
            }
        },

        elements: {
            line: {
                borderWidth: 2
            },
            point: {
                radius: 4,
                hoverRadius: 6
            }
        }
    }
});
}
*/

document.addEventListener("DOMContentLoaded", function () {

    const sportSelector = document.getElementById("sportSelector");
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");

    // chart global
    let prChart = null;

    // charge le sport et les stats
    function loadPerformance(sport) {
        const startDate = startDateInput.value || "";
        const endDate = endDateInput.value || "";

        fetch(`/api/performance?sport=${sport}&start=${startDate}&end=${endDate}`)
            .then(res => res.json())
            .then(data => {
                initChart(data, sport);
                updateStats(data);
            });
    }

    // event select sport ou date
    sportSelector.addEventListener("change", () => loadPerformance(sportSelector.value));
    startDateInput.addEventListener("change", () => loadPerformance(sportSelector.value));
    endDateInput.addEventListener("change", () => loadPerformance(sportSelector.value));

    // charge au load
    loadPerformance(sportSelector.value);

    // ---- Chart PR ----
    function initChart(data, sport) {

        const distanceMapBySport = {
            running: { "5000": "5k", "10000": "10k", "12000": "12k", "14000":"14k", "20000":"20k", "21098": "21k", "42195": "42k" },
            cycling: { "20000": "20k", "30000": "30k","40000": "40k","50000": "50k", "75000": "75k", "100000": "100k"},
            swimming: { "500": "500m", "1000": "1km", "1500": "1.5km" }
        };

        const colors = {
            "5k": "#4caf50",
            "10k": "#002fff",
            "12k": "#f3d721",
            "14k": "#f3b121c5",
            "20k": "#42a5f5",
            "21k": "#ff9800",
            "42k": "#f44336",
            "30k": "#42f5e6",
            "40k": "#42f57b",
            "50k": "#c5f542",
            "75k": "#ffb300",
            "100k": "#d32f2f",
            "500m": "#2196f3",
            "1km": "#4caf50",
            "1.5km": "#ff9800"
        };

        const distanceMap = distanceMapBySport[sport] || {};
        const datasets = [];

        Object.keys(distanceMap).forEach(distance => {
            if (!data[distance]) return;

            const label = distanceMap[distance];
            const points = data[distance].map(entry => ({
                x: entry.date,
                y: entry.value / 60
            }));

            datasets.push({
                label: label,
                data: points,
                borderColor: colors[label] || "#999",
                tension: 0.2
            });
        });

        const ctx = document.getElementById("prChart");

        if (prChart) prChart.destroy(); // reset si déjà créé

        prChart = new Chart(ctx, {
            type: "line",
            data: { datasets: datasets },
            options: {
                responsive: true,
                interaction: { mode: "nearest", intersect: false },
                plugins: {
                    legend: {
                        onHover: (event) => event.native.target.style.cursor = 'pointer',
                        onLeave: (event) => event.native.target.style.cursor = 'default',
                        onClick: function(e, legendItem, legend) {
                            const chart = legend.chart;
                            const index = legendItem.datasetIndex;
                            const visibleCount = chart.data.datasets.filter(ds => !ds.hidden).length;

                            if (visibleCount === 1) {
                                chart.data.datasets.forEach(ds => ds.hidden = false);
                            } else {
                                chart.data.datasets.forEach((ds, i) => ds.hidden = i !== index);
                            }

                            chart.update();
                        }
                    }
                },
                scales: {
                    x: { type: "time", time: { unit: "month" } },
                    y: { title: { display: true, text: "Temps (min)" } }
                },
                elements: { line: { borderWidth: 2 }, point: { radius: 4, hoverRadius: 6 } }
            }
        });
    }

    // ---- Stats ----
    function updateStats(data) {
        // calcul simple d'exemple
        // PR amélioration : (dernier PR - premier PR) / premier PR
        let allValues = [];
        Object.values(data).forEach(arr => arr.forEach(entry => allValues.push(entry.value)));

        if (allValues.length === 0) {
            document.getElementById("improvement").textContent = "0%";
            document.getElementById("weeklyVolume").textContent = "0h";
            document.getElementById("monthlyVolume").textContent = "0h";
            document.getElementById("totalVolume").textContent = "0h";
            return;
        }

        allValues.sort((a,b) => a-b);
        const first = allValues[0];
        const last = allValues[allValues.length-1];
        const improvement = ((first - last)/first*100).toFixed(1);
        document.getElementById("improvement").textContent = `${improvement}%`;

        // volume moyen exemple
        const totalSeconds = allValues.reduce((acc,v) => acc+v,0);
        const totalWeeks = 52; // placeholder
        const totalMonths = 12; // placeholder
        document.getElementById("weeklyVolume").textContent = `${(totalSeconds/(3600*totalWeeks)).toFixed(1)}h`;
        document.getElementById("monthlyVolume").textContent = `${(totalSeconds/(3600*totalMonths)).toFixed(1)}h`;
        document.getElementById("totalVolume").textContent = `${(totalSeconds/3600).toFixed(1)}h`;
    }

});

