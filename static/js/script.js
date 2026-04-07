/**
 * Student Result Query Resolution System
 * Main JavaScript – Client-Side Logic
 * All event listeners use data-attributes (no inline onclick Jinja2)
 */

/* ── Auto-dismiss flash messages ──────────────────────────── */
(function () {
  document.querySelectorAll('.flash-msg').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      el.style.opacity    = '0';
      el.style.transform  = 'translateX(30px)';
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
})();

/* ── Sidebar mobile toggle ────────────────────────────────── */
(function () {
  const mobileToggle = document.getElementById('mobileToggle');
  const sidebar      = document.querySelector('.sidebar');
  if (!mobileToggle || !sidebar) return;

  mobileToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!sidebar.contains(e.target) && !mobileToggle.contains(e.target))
      sidebar.classList.remove('open');
  });
})();

/* ── Active nav link highlight ────────────────────────────── */
(function () {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });
})();

/* ── Admin live search ────────────────────────────────────── */
(function () {
  const searchInput = document.getElementById('adminSearch');
  if (!searchInput) return;

  let timer;
  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const q     = searchInput.value.trim().toLowerCase();
      const tbody = document.getElementById('complaintTbody');
      const empty = document.getElementById('emptyState');
      if (!tbody) return;

      let visible = 0;
      tbody.querySelectorAll('tr[data-row]').forEach(row => {
        const show = !q || row.textContent.toLowerCase().includes(q);
        row.style.display = show ? '' : 'none';
        if (show) visible++;
      });

      if (empty) empty.style.display = (!q || visible > 0) ? 'none' : 'block';
    }, 300);
  });
})();

/* ── Status filter ────────────────────────────────────────── */
function filterByStatus(status) {
  const tbody = document.getElementById('complaintTbody');
  if (!tbody) return;

  document.querySelectorAll('.filter-btn').forEach(btn =>
    btn.classList.toggle('active-filter', btn.dataset.status === status)
  );

  tbody.querySelectorAll('tr[data-row]').forEach(row => {
    row.style.display = (status === 'all' ||
      (row.dataset.status || '').toLowerCase() === status.toLowerCase())
      ? '' : 'none';
  });
}

/* ── Update modal (data-attribute driven) ─────────────────── */
function openUpdateModal(id, status, subject) {
  const modal = document.getElementById('updateModal');
  if (!modal) return;

  document.getElementById('modalComplaintId').textContent = '#' + id;
  document.getElementById('modalSubject').textContent     = subject;
  document.getElementById('updateForm').action            = '/admin/update/' + id;
  document.getElementById('statusSelect').value           = status;
  document.getElementById('replyText').value              = '';

  new bootstrap.Modal(modal).show();
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.open-update-modal');
  if (!btn) return;
  const { id, status, subject } = btn.dataset;
  openUpdateModal(id, status, subject);
});

/* ── View reply (data-attribute driven) ──────────────────── */
document.addEventListener('click', e => {
  const el = e.target.closest('.view-reply-btn');
  if (!el) return;
  const reply = el.dataset.reply || '(no reply)';

  // Use a styled modal-like alert
  const existing = document.getElementById('replyAlertBox');
  if (existing) existing.remove();

  const box = document.createElement('div');
  box.id    = 'replyAlertBox';
  box.style.cssText = [
    'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);',
    'background:#1e1b4b;border:1px solid rgba(99,102,241,0.4);',
    'border-radius:12px;padding:24px 28px;max-width:420px;width:90%;',
    'z-index:9999;box-shadow:0 20px 60px rgba(0,0,0,0.6);',
    'color:#e2e8f0;font-size:0.9rem;line-height:1.6;'
  ].join('');
  box.innerHTML = `
    <div style="font-weight:700;color:#a5b4fc;margin-bottom:10px;">
      <i class="fas fa-reply me-2"></i>Admin Reply
    </div>
    <div style="color:#cbd5e1;">${reply.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>
    <div style="text-align:right;margin-top:16px;">
      <button onclick="document.getElementById('replyAlertBox').remove()"
              style="background:rgba(99,102,241,0.2);color:#a5b4fc;border:1px solid rgba(99,102,241,0.4);
                     border-radius:8px;padding:6px 18px;cursor:pointer;font-size:0.85rem;">
        Close
      </button>
    </div>`;
  document.body.appendChild(box);
});

/* ── Confirm delete (data-attribute driven) ───────────────── */
document.addEventListener('click', e => {
  const btn = e.target.closest('.confirm-delete');
  if (!btn) return;
  const id = btn.dataset.id;
  if (confirm(`Delete complaint #${id}? This action cannot be undone.`)) {
    document.getElementById('deleteForm-' + id).submit();
  }
});

/* ── Notification bell ────────────────────────────────────── */
(function () {
  const notifBtn   = document.getElementById('notifBtn');
  const notifPanel = document.getElementById('notifPanel');
  if (!notifBtn || !notifPanel) return;

  notifBtn.addEventListener('click', e => {
    e.stopPropagation();
    notifPanel.classList.toggle('show');

    if (notifPanel.classList.contains('show')) {
      fetch('/mark_notifications_read', { method: 'POST' })
        .then(() => {
          const dot = notifBtn.querySelector('.badge-dot');
          if (dot) dot.remove();
        })
        .catch(() => {});
    }
  });

  document.addEventListener('click', e => {
    if (!notifPanel.contains(e.target) && !notifBtn.contains(e.target))
      notifPanel.classList.remove('show');
  });
})();

/* ── Complaint submit loading state ───────────────────────── */
(function () {
  const form = document.getElementById('complaintForm');
  if (!form) return;
  form.addEventListener('submit', function () {
    const btn = this.querySelector('.btn-submit');
    if (btn) {
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Submitting…';
      btn.disabled  = true;
    }
  });
})();

/* ── Charts (reads from #chartDataStore data-attributes) ───── */
function initStatusChart(data) {
  const ctx = document.getElementById('statusChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Pending', 'In Progress', 'Resolved'],
      datasets: [{
        data: [data.pending, data.progress, data.resolved],
        backgroundColor: ['#f59e0b', '#3b82f6', '#10b981'],
        borderColor:     ['#f59e0b33', '#3b82f633', '#10b98133'],
        borderWidth: 2,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 11, family: 'Inter' },
                    padding: 16, usePointStyle: true }
        },
        tooltip: {
          backgroundColor: '#1a1a2e', titleColor: '#f1f5f9',
          bodyColor: '#94a3b8', borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1, padding: 12, cornerRadius: 8
        }
      }
    }
  });
}

function initIssueChart(labels, values) {
  const ctx = document.getElementById('issueChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Complaints',
        data:  values,
        backgroundColor: 'rgba(79,70,229,0.55)',
        borderColor: '#4f46e5',
        borderWidth: 1,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a2e', titleColor: '#f1f5f9',
          bodyColor: '#94a3b8', borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1, cornerRadius: 8
        }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' },
             ticks: { color: '#94a3b8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' },
             ticks: { color: '#94a3b8', font: { size: 11 }, stepSize: 1 },
             beginAtZero: true }
      }
    }
  });
}

/* ── Animate stat numbers ─────────────────────────────────── */
function animateNumbers() {
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target, 10) || 0;
    let current  = 0;
    const step   = Math.ceil(target / 25) || 1;
    const timer  = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
}

/* ── DOMContentLoaded ─────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  animateNumbers();

  // Read chart data from data-attributes on #chartDataStore
  const store = document.getElementById('chartDataStore');
  if (store) {
    const data = {
      pending:  parseInt(store.dataset.pending  || '0', 10),
      progress: parseInt(store.dataset.progress || '0', 10),
      resolved: parseInt(store.dataset.resolved || '0', 10)
    };
    const labels = JSON.parse(store.dataset.issueLabels || '[]');
    const values = JSON.parse(store.dataset.issueValues || '[]');

    initStatusChart(data);
    if (labels.length) initIssueChart(labels, values);
  }

  // Fallback: old inline window.chartData (kept for compatibility)
  if (!store && window.chartData) {
    initStatusChart(window.chartData);
    if (window.issueLabels && window.issueValues)
      initIssueChart(window.issueLabels, window.issueValues);
  }
});