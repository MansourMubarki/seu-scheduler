(async function(){
  const res = await fetch('/api/stats');
  const data = await res.json();

  // KPIs
  document.getElementById('stat-courses').textContent = data.courses_count;
  document.getElementById('stat-sessions').textContent = data.sessions_per_week;
  document.getElementById('stat-hours').textContent = data.weekly_hours;
  document.getElementById('stat-upcoming').textContent = data.upcoming_exams_30d;

  // Charts
  const modeCtx = document.getElementById('chartMode');
  new Chart(modeCtx, {
    type: 'doughnut',
    data: {
      labels: ['حضوري','عن بعد'],
      datasets: [{ data: [data.mode_counts['حضوري']||0, data.mode_counts['عن بعد']||0] }]
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
  });

  const dayCtx = document.getElementById('chartByDay');
  const dayLabels = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس'];
  new Chart(dayCtx, {
    type: 'bar',
    data: {
      labels: dayLabels,
      datasets: [{ label: 'محاضرات', data: dayLabels.map(d => data.day_counts[d]||0) }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true, precision:0 } } }
  });

  // Insights
  const list = document.getElementById('insights-list');
  list.innerHTML = '';
  data.insights.forEach(s => {
    const li = document.createElement('li'); li.textContent = s; list.appendChild(li);
  });
})();