// Keyboard Shortcuts
(function() {
  'use strict';
  var SHORTCUTS = {
    'Alt+D': function() { window.location.href = '/dashboard'; },
    'Alt+S': function() { window.location.href = '/students'; },
    'Alt+A': function() { window.location.href = '/attendance'; },
    'Alt+R': function() { window.location.href = '/reports'; },
    'Alt+C': function() { window.location.href = '/calendar'; },
    'Alt+/': function() { var el = document.querySelector('[type="search"]'); if (el) el.focus(); },
    'Escape': function() { if (document.activeElement) document.activeElement.blur(); }
  };
  document.addEventListener('keydown', function(e) {
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    var key = (e.altKey ? 'Alt+' : '') + e.key;
    var handler = SHORTCUTS[key];
    if (handler) { e.preventDefault(); handler(); }
  });
})();

// Form Validation Feedback
(function() {
  'use strict';
  function validateField(field) {
    var value = field.value.trim();
    var isValid = true;
    var message = '';
    var existing = field.parentNode.querySelector('.field-feedback');
    if (existing) existing.remove();
    if (field.required && !value) { isValid = false; message = 'This field is required.'; }
    if (isValid && field.type === 'email' && value) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) { isValid = false; message = 'Please enter a valid email.'; }
    }
    field.classList.toggle('is-invalid', !isValid);
    field.classList.toggle('is-valid', isValid && value);
    if (!isValid && message) {
      var fb = document.createElement('div');
      fb.className = 'invalid-feedback field-feedback';
      fb.textContent = message;
      field.parentNode.appendChild(fb);
    }
    return isValid;
  }
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[data-validate]').forEach(function(form) {
      form.addEventListener('submit', function(e) {
        var allValid = true;
        form.querySelectorAll('input, select, textarea').forEach(function(f) {
          if (!validateField(f)) allValid = false;
        });
        if (!allValid) e.preventDefault();
      });
      form.querySelectorAll('input, select, textarea').forEach(function(f) {
        f.addEventListener('blur', function() { validateField(f); });
        f.addEventListener('input', function() { if (f.classList.contains('is-invalid')) validateField(f); });
      });
    });
  });
})();

// Loading Skeletons
(function() {
  'use strict';
  function createSkeleton(rows, cols) {
    var container = document.createElement('div');
    container.className = 'skeleton-container';
    container.setAttribute('aria-busy', 'true');
    container.setAttribute('aria-label', 'Loading...');
    for (var i = 0; i < rows; i++) {
      var row = document.createElement('div');
      row.className = 'skeleton-row';
      for (var j = 0; j < cols; j++) {
        var cell = document.createElement('div');
        cell.className = 'skeleton-cell';
        cell.style.width = (30 + Math.random() * 70) + '%';
        row.appendChild(cell);
      }
      container.appendChild(row);
    }
    return container;
  }
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('table[data-skeleton]').forEach(function(table) {
      var rows = parseInt(table.dataset.skeleton) || 5;
      var colCount = table.querySelectorAll('thead th').length || 4;
      var skeleton = createSkeleton(rows, colCount);
      table.parentNode.insertBefore(skeleton, table);
      table.style.display = 'none';
      var observer = new MutationObserver(function() {
        if (table.querySelectorAll('tbody tr').length > 0) {
          skeleton.remove();
          table.style.display = '';
          observer.disconnect();
        }
      });
      observer.observe(table, { childList: true, subtree: true });
    });
  });
  window.createSkeleton = createSkeleton;
})();

// Breadcrumb Navigation
(function() {
  'use strict';
  document.addEventListener('DOMContentLoaded', function() {
    var container = document.getElementById('breadcrumbNav');
    if (!container) return;
    var path = window.location.pathname;
    var labels = {
      '/dashboard': 'Dashboard', '/students': 'Students', '/attendance': 'Attendance',
      '/reports': 'Reports', '/calendar': 'Calendar', '/admin': 'Administration'
    };
    var label = null;
    for (var route in labels) {
      if (path === route || path.startsWith(route + '/')) { label = labels[route]; break; }
    }
    if (!label) return;
    container.innerHTML = '<nav aria-label="breadcrumb"><ol class="breadcrumb breadcrumb-aim"><li class="breadcrumb-item"><a href="/dashboard">Home</a></li><li class="breadcrumb-item active" aria-current="page">' + label + '</li></ol></nav>';
  });
})();

// Enhanced Toast Notifications
(function() {
  'use strict';
  window.showToast = function(message, type, duration) {
    type = type || 'info';
    duration = duration || 4000;
    var container = document.getElementById('actionToastContainer');
    if (!container) return;
    var icons = {success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill'};
    var bg = {success: 'text-bg-success', error: 'text-bg-danger', warning: 'text-bg-warning', info: 'text-bg-primary'};
    var toast = document.createElement('div');
    toast.className = 'toast align-items-center ' + (bg[type] || bg.info) + ' border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = '<div class="d-flex"><div class="toast-body"><i class="bi ' + (icons[type] || icons.info) + ' me-2"></i>' + message + '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    container.appendChild(toast);
    if (typeof bootstrap !== 'undefined') {
      var inst = bootstrap.Toast.getOrCreateInstance(toast, { delay: duration });
      toast.addEventListener('hidden.bs.toast', function() { toast.remove(); }, { once: true });
      inst.show();
    }
  };
})();

// Focus Indicators & Accessibility
(function() {
  'use strict';
  document.addEventListener('focusin', function(e) {
    if (e.target.matches('a, button, input, select, textarea, [tabindex]')) e.target.classList.add('focus-visible');
  });
  document.addEventListener('focusout', function(e) { e.target.classList.remove('focus-visible'); });
  window.announceToScreenReader = function(message) {
    var el = document.getElementById('srAnnouncer');
    if (!el) {
      el = document.createElement('div');
      el.id = 'srAnnouncer';
      el.className = 'sr-only';
      el.setAttribute('aria-live', 'polite');
      el.style.cssText = 'position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden;';
      document.body.appendChild(el);
    }
    el.textContent = message;
  };
})();
