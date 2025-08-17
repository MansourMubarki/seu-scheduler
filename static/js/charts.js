// Simple chart helpers (Chart.js v4 via CDN in templates)
function makeCharts(stats){
  // Doughnut: lectures onsite/online vs exams
  const ctx1 = document.getElementById('doughnut');
  if(ctx1){
    new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: ['حضوري', 'عن بعد', 'اختبارات'],
        datasets: [{
          data: [stats.onsite_count, stats.online_count, stats.exam_count],
        }]
      },
      options: {
        plugins:{legend:{position:'bottom'}},
        maintainAspectRatio:false
      }
    });
  }

  // Bar: عدد المحاضرات لكل يوم
  const ctx2 = document.getElementById('byday');
  if(ctx2){
    new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: stats.days_ar,
        datasets: [{
          label: 'عدد المحاضرات',
          data: stats.counts_by_day,
        }]
      },
      options: {
        plugins:{legend:{display:false}},
        maintainAspectRatio:false
      }
    });
  }
}

function printTable(){
  window.print();
}
