let pieChart;

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  const parts = [];
  if (h) parts.push(`${h}h`);
  if (m) parts.push(`${m}m`);
  if (s || parts.length === 0) parts.push(`${s}s`);

  return parts.join(' ');
}


function updatePieChart(zones) {

    const data = [
        zones.Nodata,
        zones.z0,
        zones.z1,
        zones.z2,
        zones.z3,
        zones.z4,
        zones.z5
    ];

    if (pieChart) {
        pieChart.data.datasets[0].data = data;
        pieChart.update();
        return;
    }

    pieChart = new Chart(document.getElementById("hrPie"), {
        type: "pie",
        data: {
            labels: ["No data", "Z0", "Z1", "Z2", "Z3", "Z4", "Z5"],
            datasets: [{
                data: data,
                backgroundColor: [
                    "#000000", // NoValue
                    "#d6d6d6", // Z0 → gris clair
                    "#757575",
                    "#2196f3",
                    "#4caf50",
                    "#ff9800",
                    "#f44336"
                ]
            }]
        },
        options: {
            plugins: {
                datalabels: {
                    color: "#fff",
                    align: "end",
                    offset: 16,
                    formatter: (value, context) => {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        if (!total || value === 0) return "";
                        return ((value / total) * 100).toFixed(1) + "%";
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                        const label = context.label || '';
                        const value = context.raw; // valeur en secondes
                        return `${label}: ${formatDuration(value)}`;
                        }
                    }
                },
            }
        },
        plugins: [ChartDataLabels]
    });
}
