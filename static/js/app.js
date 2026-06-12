(function () {
  const KEYS = {
    sidebarCollapsed: "aim.sidebar.collapsed",
    sidebarScroll: "aim.sidebar.scroll",
  };

  const SELECTORS = {
    loader: "#pageLoader",
    sidebar: "[data-sidebar-scroll]",
    sidebarToggle: "[data-sidebar-toggle]",
    mobileToggle: "[data-mobile-nav-toggle]",
    mobileClose: "[data-mobile-nav-close]",
    backdrop: "[data-shell-backdrop]",
    notificationToggle: "[data-notification-toggle]",
    notificationMenu: "#notificationMenu",
    confirmModal: "#confirmModal",
    confirmTitle: "#confirmModalTitle",
    confirmBody: "#confirmModalBody",
    confirmIcon: "#confirmModalIcon",
    confirmButton: "#confirmModalButton",
    logoutModal: "#logoutModal",
  };

  let confirmCallback = null;

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }
    callback();
  }

  function getTheme() {
    return document.body.classList.contains("theme-dark") ? "dark" : "light";
  }

  function showPageLoader() {
    const loader = $(SELECTORS.loader);
    if (loader) loader.classList.add("active");
  }

  function hidePageLoader() {
    const loader = $(SELECTORS.loader);
    if (loader) loader.classList.remove("active");
  }

  function setSidebarCollapsed(collapsed, persist) {
    document.documentElement.dataset.sidebarCollapsed = collapsed ? "1" : "0";
    document.body.classList.toggle("sidebar-collapsed", collapsed);

    const toggle = $(SELECTORS.sidebarToggle);
    if (toggle) {
      const icon = $("i", toggle);
      const label = $(".sidebar-link__label", toggle);
      if (icon) {
        icon.className = collapsed ? "bi bi-layout-sidebar-inset-reverse" : "bi bi-layout-sidebar-inset";
      }
      if (label) {
        label.textContent = collapsed ? "Expand sidebar" : "Collapse sidebar";
      }
    }

    if (persist) {
      try {
        localStorage.setItem(KEYS.sidebarCollapsed, collapsed ? "1" : "0");
      } catch (error) {
        console.warn(error);
      }
    }
  }

  function restoreSidebarState() {
    try {
      setSidebarCollapsed(localStorage.getItem(KEYS.sidebarCollapsed) === "1", false);
    } catch (error) {
      setSidebarCollapsed(false, false);
    }
  }

  function saveSidebarScroll() {
    const sidebar = $(SELECTORS.sidebar);
    if (!sidebar) return;
    try {
      sessionStorage.setItem(KEYS.sidebarScroll, String(sidebar.scrollTop || 0));
    } catch (error) {
      console.warn(error);
    }
  }

  function restoreSidebarScroll() {
    const sidebar = $(SELECTORS.sidebar);
    if (!sidebar) return;
    try {
      const saved = sessionStorage.getItem(KEYS.sidebarScroll);
      if (saved === null) return;
      requestAnimationFrame(function () {
        sidebar.scrollTop = parseInt(saved, 10) || 0;
      });
    } catch (error) {
      console.warn(error);
    }
  }

  function setMobileNav(open) {
    document.body.classList.toggle("nav-open", open);
  }

  function toggleNotifications(forceOpen) {
    const menu = $(SELECTORS.notificationMenu);
    const toggle = $(SELECTORS.notificationToggle);
    if (!menu || !toggle) return;

    const nextOpen = typeof forceOpen === "boolean" ? forceOpen : menu.hasAttribute("hidden");
    if (nextOpen) {
      menu.removeAttribute("hidden");
      toggle.setAttribute("aria-expanded", "true");
    } else {
      menu.setAttribute("hidden", "");
      toggle.setAttribute("aria-expanded", "false");
    }
  }

  function updateAttendanceSelect(select) {
    if (!select) return;
    select.dataset.status = select.value || "";
  }

  function updatePasswordToggle(button) {
    const target = document.getElementById(button.dataset.passwordToggle);
    if (!target) return;

    const visible = target.type === "password";
    target.type = visible ? "text" : "password";
    button.dataset.visible = visible ? "true" : "false";
    button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    button.setAttribute("aria-pressed", visible ? "true" : "false");

    const icon = $(".password-toggle-icon", button);
    if (icon) {
      icon.className = visible ? "bi bi-eye-slash-fill password-toggle-icon" : "bi bi-eye-fill password-toggle-icon";
    }
  }

  function showActionToast(message, variant) {
    const container = document.getElementById("actionToastContainer");
    if (!container || typeof bootstrap === "undefined") return;

    const toast = document.createElement("div");
    toast.className = "toast align-items-center text-bg-" + (variant || "primary") + " border-0";
    toast.innerHTML =
      "<div class=\"d-flex\">" +
      "<div class=\"toast-body\">" + message + "</div>" +
      "<button type=\"button\" class=\"btn-close btn-close-white me-2 m-auto\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>" +
      "</div>";
    container.appendChild(toast);

    const instance = bootstrap.Toast.getOrCreateInstance(toast, { delay: 2600 });
    toast.addEventListener("hidden.bs.toast", function () {
      toast.remove();
    }, { once: true });
    instance.show();
  }

  async function downloadFile(url, filename, message) {
    showPageLoader();
    try {
      const response = await fetch(url, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) {
        throw new Error("Download failed: " + response.status);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename || url.split("/").pop() || "download";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(function () {
        URL.revokeObjectURL(objectUrl);
      }, 1000);
      showActionToast(message || "Download completed.", "success");
    } catch (error) {
      console.error(error);
      showActionToast("Download failed.", "danger");
    } finally {
      window.setTimeout(hidePageLoader, 150);
    }
  }

  function openConfirmModal(options) {
    const modalElement = $(SELECTORS.confirmModal);
    if (!modalElement || typeof bootstrap === "undefined") return;

    const title = $(SELECTORS.confirmTitle);
    const body = $(SELECTORS.confirmBody);
    const icon = $(SELECTORS.confirmIcon);
    const button = $(SELECTORS.confirmButton);

    if (title) title.textContent = options.title || "Confirm";
    if (body) body.textContent = options.message || "Are you sure?";
    if (icon) icon.className = "bi " + (options.icon || "bi-question-circle");
    if (button) {
      button.className = "btn " + (options.confirmClass || "btn-ui-primary");
      button.innerHTML = "<i class=\"bi " + (options.icon || "bi-check-circle") + "\" aria-hidden=\"true\"></i><span>" + (options.confirmText || "Confirm") + "</span>";
    }

    confirmCallback = typeof options.onConfirm === "function" ? options.onConfirm : null;
    bootstrap.Modal.getOrCreateInstance(modalElement).show();
  }

  function runConfirmModal() {
    const modalElement = $(SELECTORS.confirmModal);
    if (modalElement && typeof bootstrap !== "undefined") {
      bootstrap.Modal.getOrCreateInstance(modalElement).hide();
    }
    if (typeof confirmCallback === "function") {
      const callback = confirmCallback;
      confirmCallback = null;
      callback();
    }
  }

  function openLogoutModal() {
    const modalElement = $(SELECTORS.logoutModal);
    if (modalElement && typeof bootstrap !== "undefined") {
      bootstrap.Modal.getOrCreateInstance(modalElement).show();
    }
  }

  function bindFormLoaders() {
    $all("form").forEach(function (form) {
      if (form.dataset.noLoader === "1") return;
      form.addEventListener("submit", function () {
        showPageLoader();
      });
    });
  }

  function bindSortableTables() {
    $all("table[data-sortable]").forEach(function (table) {
      $all("[data-sort-column]", table).forEach(function (button) {
        button.addEventListener("click", function () {
          const column = parseInt(button.dataset.sortColumn, 10);
          const currentColumn = table.dataset.sortColumn;
          const currentDirection = table.dataset.sortDirection || "asc";
          const ascending = currentColumn !== String(column) || currentDirection !== "asc";
          const rows = Array.from(table.tBodies[0].rows);

          rows.sort(function (leftRow, rightRow) {
            const left = leftRow.cells[column]?.textContent?.trim() || "";
            const right = rightRow.cells[column]?.textContent?.trim() || "";
            return ascending
              ? left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" })
              : right.localeCompare(left, undefined, { numeric: true, sensitivity: "base" });
          });

          rows.forEach(function (row) {
            table.tBodies[0].appendChild(row);
          });

          table.dataset.sortColumn = String(column);
          table.dataset.sortDirection = ascending ? "asc" : "desc";
          $all("[data-sort-column]", table).forEach(function (header) {
            header.dataset.sortDirection = "";
          });
          button.dataset.sortDirection = ascending ? "asc" : "desc";
        });
      });
    });
  }

  function bindYearGroups() {
    $all("[data-year-group]").forEach(function (group) {
      const prefix = $("[data-year-prefix]", group);
      const suffix = $("[data-year-suffix]", group);
      const hidden = $("[data-year-hidden]", group);
      if (!prefix || !suffix || !hidden) return;

      function syncYear() {
        const year = (prefix.value || "").replace(/\D/g, "").slice(0, 4);
        prefix.value = year;
        if (year.length === 4) {
          const next = String(parseInt(year, 10) + 1).slice(-2);
          suffix.value = next;
          hidden.value = year + "-" + next;
        } else {
          suffix.value = "";
          hidden.value = year;
        }
      }

      ["input", "change", "paste"].forEach(function (eventName) {
        prefix.addEventListener(eventName, function () {
          window.setTimeout(syncYear, 0);
        });
      });

      syncYear();
    });
  }

  function getChartPalette() {
    const dark = getTheme() === "dark";
    return {
      text: dark ? "#e7eff8" : "#213449",
      grid: dark ? "rgba(148, 163, 184, 0.18)" : "rgba(15, 23, 42, 0.1)",
      brand: dark ? "#63a7ff" : "#1d4ed8",
      brandSoft: dark ? "rgba(99, 167, 255, 0.2)" : "rgba(29, 78, 216, 0.12)",
      success: "#0f9f6e",
      warning: "#f5bd42",
      danger: "#cf4d48",
    };
  }

  function animateCount(element, value, duration) {
    const target = Number(value) || 0;
    const start = performance.now();

    function frame(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = String(Math.round(target * eased));
      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    }

    requestAnimationFrame(frame);
  }

  function initDashboardCharts() {
    if (typeof Chart === "undefined") return;
    const dataScript = document.getElementById("dashboard-chart-data");
    if (!dataScript) return;

    const data = JSON.parse(dataScript.textContent);
    const palette = getChartPalette();
    Chart.defaults.color = palette.text;
    Chart.defaults.font.family = '"IBM Plex Sans", "Segoe UI", sans-serif';

    const summary = document.getElementById("attendanceSummaryChart");
    if (summary) {
      new Chart(summary, {
        type: "doughnut",
        data: {
          labels: ["Present", "Absent", "Leave"],
          datasets: [{
            data: [data.present, data.absent, data.leave],
            backgroundColor: [palette.success, palette.danger, palette.warning],
            borderWidth: 0,
            hoverOffset: 8,
          }],
        },
        options: {
          cutout: "70%",
          plugins: {
            legend: {
              position: "bottom",
              labels: { color: palette.text, usePointStyle: true, padding: 18 },
            },
          },
        },
      });
    }

    const trend = document.getElementById("attendanceTrendChart");
    if (trend) {
      new Chart(trend, {
        type: "line",
        data: {
          labels: data.monthLabels,
          datasets: [{
            label: "Attendance %",
            data: data.months,
            borderColor: palette.brand,
            backgroundColor: palette.brandSoft,
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointHoverRadius: 6,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: palette.text }, grid: { color: palette.grid } },
            y: { beginAtZero: true, suggestedMax: 100, ticks: { color: palette.text }, grid: { color: palette.grid } },
          },
        },
      });
    }

    $all("[data-count-up]").forEach(function (item) {
      animateCount(item, item.dataset.countUp, 850);
    });
  }

  function initStudentChart() {
    if (typeof Chart === "undefined") return;
    const dataScript = document.getElementById("student-chart-data");
    const chart = document.getElementById("studentChart");
    if (!dataScript || !chart) return;

    const data = JSON.parse(dataScript.textContent);
    const palette = getChartPalette();
    const statusMap = { 0: "Absent", 1: "Leave", 2: "Present" };

    new Chart(chart, {
      type: "line",
      data: {
        labels: data.dates,
        datasets: [{
          data: data.values,
          borderColor: palette.brand,
          backgroundColor: palette.brandSoft,
          fill: true,
          stepped: true,
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: palette.text }, grid: { color: palette.grid } },
          y: {
            min: 0,
            max: 2,
            ticks: {
              stepSize: 1,
              color: palette.text,
              callback: function (value) {
                return statusMap[value] || "";
              },
            },
            grid: { color: palette.grid },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Status: " + (statusMap[context.parsed.y] || "Unknown");
              },
            },
          },
        },
      },
    });
  }

  function initCalendar() {
    if (typeof FullCalendar === "undefined") return;
    const calendar = document.getElementById("attendanceCalendar");
    const configScript = document.getElementById("calendar-config");
    if (!calendar || !configScript) return;

    const config = JSON.parse(configScript.textContent);
    const instance = new FullCalendar.Calendar(calendar, {
      initialView: "dayGridMonth",
      height: 680,
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "dayGridMonth,timeGridWeek",
      },
      buttonText: {
        today: "Today",
        month: "Month",
        week: "Week",
      },
      events: config.eventsUrl,
      dateClick: function (info) {
        if (config.isTeacher && (info.dateStr < config.policyStart || info.dateStr > config.policyEnd)) {
          return;
        }
        window.location.href = config.attendanceUrl + "?date=" + encodeURIComponent(info.dateStr);
      },
      eventDidMount: function (info) {
        info.el.title = info.event.title;
      },
    });
    instance.render();
  }

  async function pollSessionStatus() {
    if (document.body.dataset.authenticated !== "1") return;
    try {
      const response = await fetch("/session_status", {
        credentials: "same-origin",
        cache: "no-store",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) {
        window.location.replace("/login");
      }
    } catch (error) {
      window.location.replace("/login");
    }
  }

  function startSessionPolling() {
    if (document.body.dataset.authenticated !== "1") return;
    pollSessionStatus();
    window.setInterval(pollSessionStatus, 30000);
  }

  function bindGlobalActions() {
    document.addEventListener("click", function (event) {
      const sidebarToggle = event.target.closest(SELECTORS.sidebarToggle);
      if (sidebarToggle) {
        event.preventDefault();
        setSidebarCollapsed(document.documentElement.dataset.sidebarCollapsed !== "1", true);
        return;
      }

      if (event.target.closest(SELECTORS.mobileToggle)) {
        event.preventDefault();
        setMobileNav(true);
        return;
      }

      if (event.target.closest(SELECTORS.mobileClose) || event.target.closest(SELECTORS.backdrop)) {
        event.preventDefault();
        setMobileNav(false);
        return;
      }

      const notificationToggle = event.target.closest(SELECTORS.notificationToggle);
      if (notificationToggle) {
        event.preventDefault();
        toggleNotifications();
        return;
      }

      const passwordToggle = event.target.closest("[data-password-toggle]");
      if (passwordToggle) {
        event.preventDefault();
        updatePasswordToggle(passwordToggle);
        return;
      }

      const pickerToggle = event.target.closest("[data-open-picker]");
      if (pickerToggle) {
        event.preventDefault();
        const field = document.getElementById(pickerToggle.dataset.openPicker);
        if (field) {
          if (typeof field.showPicker === "function") {
            field.showPicker();
          } else {
            field.focus();
          }
        }
        return;
      }

      const bulkButton = event.target.closest("[data-attendance-bulk]");
      if (bulkButton) {
        event.preventDefault();
        const status = bulkButton.dataset.attendanceBulk;
        $all(".attendance-status").forEach(function (select) {
          select.value = status;
          updateAttendanceSelect(select);
        });
        // Mark which bulk button is active
        $all("[data-attendance-bulk]").forEach(function (btn) {
          btn.dataset.active = "0";
        });
        bulkButton.dataset.active = "1";
        return;
      }

      const randomizeBtn = event.target.closest("[data-attendance-randomize]");
      if (randomizeBtn) {
        event.preventDefault();
        const dateInput = document.querySelector("[name='date'], [name='attendance_date']");
        const targetDate = dateInput ? dateInput.value : "";
        const csrfToken = document.querySelector("[name='csrf_token']");
        const csrf = csrfToken ? csrfToken.value : "";

        randomizeBtn.disabled = true;
        const icon = randomizeBtn.querySelector("i");
        if (icon) icon.className = "bi bi-arrow-repeat spinning";

        fetch("/api/attendance/randomize", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
          },
          body: JSON.stringify({ date: targetDate }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.ok) {
              showActionToast(data.message, "success");
              // Reload the page to reflect the new attendance
              window.setTimeout(function () { window.location.reload(); }, 1200);
            } else {
              showActionToast(data.message || "Failed to generate attendance.", "danger");
              randomizeBtn.disabled = false;
              if (icon) icon.className = "bi bi-dice-3";
            }
          })
          .catch(function () {
            showActionToast("Network error. Please try again.", "danger");
            randomizeBtn.disabled = false;
            if (icon) icon.className = "bi bi-dice-3";
          });
        return;
      }

      const confirmForm = event.target.closest("[data-confirm-form]");
      if (confirmForm) {
        event.preventDefault();
        const form = document.getElementById(confirmForm.dataset.confirmForm);
        if (!form) return;
        openConfirmModal({
          title: confirmForm.dataset.confirmTitle,
          message: confirmForm.dataset.confirmMessage,
          confirmText: confirmForm.dataset.confirmLabel,
          confirmClass: confirmForm.dataset.confirmClass,
          icon: confirmForm.dataset.confirmIcon,
          onConfirm: function () {
            form.submit();
          },
        });
        return;
      }

      const confirmHref = event.target.closest("[data-confirm-href]");
      if (confirmHref) {
        event.preventDefault();
        openConfirmModal({
          title: confirmHref.dataset.confirmTitle,
          message: confirmHref.dataset.confirmMessage,
          confirmText: confirmHref.dataset.confirmLabel,
          confirmClass: confirmHref.dataset.confirmClass,
          icon: confirmHref.dataset.confirmIcon,
          onConfirm: function () {
            window.location.href = confirmHref.dataset.confirmHref;
          },
        });
        return;
      }

      const downloadTrigger = event.target.closest("[data-download-url]");
      if (downloadTrigger) {
        event.preventDefault();
        downloadFile(downloadTrigger.dataset.downloadUrl, downloadTrigger.dataset.downloadFilename, downloadTrigger.dataset.downloadMessage);
        return;
      }

      if (event.target.closest("[data-open-logout]")) {
        event.preventDefault();
        openLogoutModal();
      }
    });

    document.addEventListener("change", function (event) {
      const redirectField = event.target.closest("[data-redirect-base]");
      if (!redirectField) return;
      window.location.href = redirectField.dataset.redirectBase + encodeURIComponent(redirectField.value);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setMobileNav(false);
        toggleNotifications(false);
      }
    });

    document.addEventListener("click", function (event) {
      const menu = $(SELECTORS.notificationMenu);
      const toggle = $(SELECTORS.notificationToggle);
      if (!menu || !toggle || menu.hasAttribute("hidden")) return;
      if (menu.contains(event.target) || toggle.contains(event.target)) return;
      toggleNotifications(false);
    });
  }

  onReady(function () {
    restoreSidebarState();
    restoreSidebarScroll();
    bindGlobalActions();
    bindFormLoaders();
    bindSortableTables();
    bindYearGroups();
    initDashboardCharts();
    initStudentChart();
    initCalendar();

    $all(".attendance-status").forEach(updateAttendanceSelect);
    const confirmButton = $(SELECTORS.confirmButton);
    if (confirmButton) {
      confirmButton.addEventListener("click", runConfirmModal);
    }

    const sidebar = $(SELECTORS.sidebar);
    if (sidebar) {
      sidebar.addEventListener("scroll", saveSidebarScroll, { passive: true });
      window.addEventListener("beforeunload", saveSidebarScroll);
      window.addEventListener("pagehide", saveSidebarScroll);
    }

    window.addEventListener("load", hidePageLoader, { once: true });
    window.setTimeout(hidePageLoader, 220);
    startSessionPolling();
  });

  window.openConfirmModal = openConfirmModal;
  window.runConfirmModal = runConfirmModal;
  window.downloadFile = downloadFile;
  window.showPageLoader = showPageLoader;
  window.hidePageLoader = hidePageLoader;
  window.openLogoutModal = openLogoutModal;
  window.showActionToast = showActionToast;
})();
