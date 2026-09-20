document.addEventListener('DOMContentLoaded', function () {
  function esc(s) {
    return (s == null ? '' : String(s)).replace(/[&<>"]/g, function (c) {
      return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c];
    });
  }
  function updateCount() {
    var n = document.querySelectorAll('#notif-grid .notif-card').length;
    var badge = document.getElementById('notif-count');
    var panel = document.getElementById('notif-panel');
    if (badge) badge.textContent = n;
    if (panel) panel.style.display = n ? '' : 'none';
  }

  fetch('/drivers/fetch-pmissions/')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var pmissions = data.pmissions || [];
      var grid = document.getElementById('notif-grid');
      if (!grid) return;

      // ---- group by customer + from_location + to_location ----
      var groups = {};
      var order = [];
      function norm(s) {
        return (s == null ? '' : String(s)).trim().replace(/\s+/g, ' ').toLowerCase();
      }
      pmissions.forEach(function (m) {
        var key = [norm(m.customer_name), norm(m.from_location), norm(m.to_location)].join('||');
        if (!groups[key]) {
          groups[key] = {
            customer_name: m.customer_name,
            from_location: m.from_location,
            to_location: m.to_location,
            ids: [],
            cars: [],
          };
          order.push(key);
        }
        groups[key].ids.push(m.id);
        // collect vehicle numbers (skip blanks / duplicates)
        var num = (m.car_num == null ? '' : String(m.car_num)).trim();
        if (num && groups[key].cars.indexOf(num) === -1) {
          groups[key].cars.push(num);
        }
      });

      order.forEach(function (key) {
        var g = groups[key];
        var count = g.cars.length || g.ids.length;
        var carsText = g.cars.length ? g.cars.join(' , ') : '—';

        var col = document.createElement('div');
        col.className = 'col-12 col-sm-6 col-lg-4 col-xl-3 notif-card';
        col.innerHTML =
          '<div class="card h-100 shadow-sm border-start border-warning" style="border-left-width:4px;">' +
            '<div class="card-header d-flex justify-content-between align-items-center py-2">' +
              '<strong class="text-truncate" title="' + esc(g.customer_name) + '">' + esc(g.customer_name) + '</strong>' +
              '<div class="d-flex align-items-center">' +
                '<span class="badge bg-primary me-2" title="Vehicles">' + count + '</span>' +
                '<button type="button" class="btn-close notif-dismiss" aria-label="Mark as read"></button>' +
              '</div>' +
            '</div>' +
            '<div class="card-body py-2">' +
              '<div class="mb-1"><i class="fas fa-map-marker-alt text-success"></i> <strong>From:</strong> ' + esc(g.from_location) + '</div>' +
              '<div class="mb-1"><i class="fas fa-flag-checkered text-danger"></i> <strong>To:</strong> ' + esc(g.to_location) + '</div>' +
              '<div><i class="fas fa-truck text-primary"></i> <strong>Vehicles (' + count + '):</strong> ' +
                '<span class="text-muted">' + esc(carsText) + '</span></div>' +
            '</div>' +
          '</div>';
        grid.appendChild(col);

        col.querySelector('.notif-dismiss').addEventListener('click', function (e) {
          e.stopPropagation();
          markAsReadBulk(g.ids);   // one request for the whole group
          col.remove();
          updateCount();
        });
      });

      updateCount();
    })
    .catch(function (error) { console.error('Error fetching PMissions:', error); });

  function markAsRead(missionId) {
    fetch('/drivers/mark-as-read/' + missionId + '/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' }
    }).then(function (r) { return r.json(); })
      .catch(function (error) { console.error('Error marking as read:', error); });
  }

  function markAsReadBulk(ids) {
    fetch('/drivers/mark-as-read-bulk/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: ids })
    }).then(function (r) { return r.json(); })
      .catch(function (error) { console.error('Error marking group as read:', error); });
  }

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});