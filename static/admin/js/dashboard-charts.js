// Dashboard Charts
// This file contains all the JavaScript functionality for the admin dashboard charts

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeUserActivityChart();
    initializeTransactionChart();
    initializeUserGrowthChart();
    initializeProgressBars();
    setupChartOptions();
});

// User Activity Chart - Shows daily active users over time
function initializeUserActivityChart() {
    var userCtx = document.getElementById("userActivityChart");
    if (!userCtx) return;
    
    var activityDates = JSON.parse(userCtx.getAttribute('data-dates') || '[]');
    var activityValues = JSON.parse(userCtx.getAttribute('data-values') || '[]');
    
    var userActivityChart = new Chart(userCtx, {
        type: 'line',
        data: {
            labels: activityDates,
            datasets: [{
                label: "Active Users",
                lineTension: 0.3,
                backgroundColor: "rgba(78, 115, 223, 0.05)",
                borderColor: "rgba(78, 115, 223, 1)",
                pointRadius: 3,
                pointBackgroundColor: "rgba(78, 115, 223, 1)",
                pointBorderColor: "rgba(78, 115, 223, 1)",
                pointHoverRadius: 3,
                pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
                pointHoverBorderColor: "rgba(78, 115, 223, 1)",
                pointHitRadius: 10,
                pointBorderWidth: 2,
                data: activityValues
            }]
        },
        options: {
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 10,
                    right: 25,
                    top: 25,
                    bottom: 0
                }
            },
            scales: {
                xAxes: [{
                    time: {
                        unit: 'date'
                    },
                    gridLines: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 7
                    }
                }],
                yAxes: [{
                    ticks: {
                        maxTicksLimit: 5,
                        padding: 10,
                        beginAtZero: true,
                        callback: function(value, index, values) {
                            return value;
                        }
                    },
                    gridLines: {
                        color: "rgb(234, 236, 244)",
                        zeroLineColor: "rgb(234, 236, 244)",
                        drawBorder: false,
                        borderDash: [2],
                        zeroLineBorderDash: [2]
                    }
                }]
            },
            legend: {
                display: false
            },
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                titleMarginBottom: 10,
                titleFontColor: '#6e707e',
                titleFontSize: 14,
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                intersect: false,
                mode: 'index',
                caretPadding: 10,
                callbacks: {
                    label: function(tooltipItem, chart) {
                        var datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
                        return datasetLabel + ': ' + tooltipItem.yLabel;
                    }
                }
            }
        }
    });
}

// Transaction Chart - Shows deposit and withdrawal volumes
function initializeTransactionChart() {
    var txCtx = document.getElementById("transactionChart");
    if (!txCtx) return;
    
    var txDates = JSON.parse(txCtx.getAttribute('data-dates') || '[]');
    var depositValues = JSON.parse(txCtx.getAttribute('data-deposits') || '[]');
    var withdrawalValues = JSON.parse(txCtx.getAttribute('data-withdrawals') || '[]');
    
    var transactionChart = new Chart(txCtx, {
        type: 'line',
        data: {
            labels: txDates,
            datasets: [{
                label: "Deposits",
                lineTension: 0.3,
                backgroundColor: "rgba(28, 200, 138, 0.05)",
                borderColor: "rgba(28, 200, 138, 1)",
                pointRadius: 3,
                pointBackgroundColor: "rgba(28, 200, 138, 1)",
                pointBorderColor: "rgba(28, 200, 138, 1)",
                pointHoverRadius: 3,
                pointHoverBackgroundColor: "rgba(28, 200, 138, 1)",
                pointHoverBorderColor: "rgba(28, 200, 138, 1)",
                pointHitRadius: 10,
                pointBorderWidth: 2,
                data: depositValues
            },
            {
                label: "Withdrawals",
                lineTension: 0.3,
                backgroundColor: "rgba(231, 74, 59, 0.05)",
                borderColor: "rgba(231, 74, 59, 1)",
                pointRadius: 3,
                pointBackgroundColor: "rgba(231, 74, 59, 1)",
                pointBorderColor: "rgba(231, 74, 59, 1)",
                pointHoverRadius: 3,
                pointHoverBackgroundColor: "rgba(231, 74, 59, 1)",
                pointHoverBorderColor: "rgba(231, 74, 59, 1)",
                pointHitRadius: 10,
                pointBorderWidth: 2,
                data: withdrawalValues
            }]
        },
        options: {
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 10,
                    right: 25,
                    top: 25,
                    bottom: 0
                }
            },
            scales: {
                xAxes: [{
                    time: {
                        unit: 'date'
                    },
                    gridLines: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 7
                    }
                }],
                yAxes: [{
                    ticks: {
                        maxTicksLimit: 5,
                        padding: 10,
                        beginAtZero: true,
                        callback: function(value, index, values) {
                            return '$' + value;
                        }
                    },
                    gridLines: {
                        color: "rgb(234, 236, 244)",
                        zeroLineColor: "rgb(234, 236, 244)",
                        drawBorder: false,
                        borderDash: [2],
                        zeroLineBorderDash: [2]
                    }
                }]
            },
            legend: {
                display: true
            },
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                titleMarginBottom: 10,
                titleFontColor: '#6e707e',
                titleFontSize: 14,
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                intersect: false,
                mode: 'index',
                caretPadding: 10,
                callbacks: {
                    label: function(tooltipItem, chart) {
                        var datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
                        return datasetLabel + ': $' + tooltipItem.yLabel;
                    }
                }
            }
        }
    });
}

// User Growth Chart - Shows new users over time
function initializeUserGrowthChart() {
    var growthCtx = document.getElementById("userGrowthChart");
    if (!growthCtx) return;
    
    var growthDates = JSON.parse(growthCtx.getAttribute('data-dates') || '[]');
    var growthValues = JSON.parse(growthCtx.getAttribute('data-values') || '[]');
    
    var userGrowthChart = new Chart(growthCtx, {
        type: 'bar',
        data: {
            labels: growthDates,
            datasets: [{
                label: "New Users",
                backgroundColor: "rgba(78, 115, 223, 0.8)",
                borderColor: "rgba(78, 115, 223, 1)",
                data: growthValues
            }]
        },
        options: {
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 10,
                    right: 25,
                    top: 25,
                    bottom: 0
                }
            },
            scales: {
                xAxes: [{
                    time: {
                        unit: 'date'
                    },
                    gridLines: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 7
                    }
                }],
                yAxes: [{
                    ticks: {
                        min: 0,
                        maxTicksLimit: 5,
                        padding: 10,
                        callback: function(value, index, values) {
                            return value;
                        }
                    },
                    gridLines: {
                        color: "rgb(234, 236, 244)",
                        zeroLineColor: "rgb(234, 236, 244)",
                        drawBorder: false,
                        borderDash: [2],
                        zeroLineBorderDash: [2]
                    }
                }]
            },
            legend: {
                display: false
            },
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                titleMarginBottom: 10,
                titleFontColor: '#6e707e',
                titleFontSize: 14,
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                intersect: false,
                mode: 'index',
                caretPadding: 10,
                callbacks: {
                    label: function(tooltipItem, chart) {
                        var datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
                        return datasetLabel + ': ' + tooltipItem.yLabel;
                    }
                }
            }
        }
    });
}

// Initialize progress bars
function initializeProgressBars() {
    const progressBars = {
        'cpuProgressBar': document.getElementById('cpuProgressBar'),
        'memoryProgressBar': document.getElementById('memoryProgressBar'),
        'diskProgressBar': document.getElementById('diskProgressBar'),
        'connProgressBar': document.getElementById('connProgressBar'),
        'responseProgressBar': document.getElementById('responseProgressBar')
    };

    Object.entries(progressBars).forEach(([key, bar]) => {
        if (bar) {
            const value = bar.getAttribute('aria-valuenow');
            bar.style.width = `${value}%`;
        }
    });
}

// Setup chart option buttons
function setupChartOptions() {
    // Add event listeners to period selectors
    document.querySelectorAll('[data-period]').forEach(button => {
        button.addEventListener('click', function() {
            const period = this.dataset.period;
            const chartId = this.closest('.card').querySelector('canvas').id;
            
            // Remove active class from all buttons in the group
            this.parentElement.querySelectorAll('.dropdown-item').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Here you would typically make an AJAX call to fetch new data
            console.log(`Changing ${chartId} to display ${period} days of data`);
            // In production, would fetch new data and update the chart
        });
    });
} 