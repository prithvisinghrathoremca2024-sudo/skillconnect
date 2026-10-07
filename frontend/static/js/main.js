document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alert popups after 4 seconds
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 4000);
  });
});