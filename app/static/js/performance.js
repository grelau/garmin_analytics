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
                initChart(data['pr'], sport);
                updateStats(data['training']);
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

        document.getElementById("improvement").textContent = `4%`;

        document.getElementById("weeklyVolume").textContent = `${data.weekly_distance}km`;
        document.getElementById("monthlyVolume").textContent = `${data.monthly_distance}km`;
        document.getElementById("totalVolume").textContent = `${data.total_distance}km`;
    }
});

