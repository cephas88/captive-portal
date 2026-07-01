(function () {
  "use strict";

  var selectedPackage  = null;
  var currentSessionId = null;
  var pollInterval     = null;

  var packageCards    = document.querySelectorAll(".package-card");
  var packagesSection = document.querySelector(".packages");
  var paymentForm     = document.getElementById("payment-form");
  var selectedBanner  = document.getElementById("selected-pkg-banner");
  var phoneInput      = document.getElementById("phone");
  var btnPay          = document.getElementById("btn-pay");
  var btnPayText      = document.getElementById("btn-pay-text");
  var btnPaySpinner   = document.getElementById("btn-pay-spinner");
  var btnBack         = document.getElementById("btn-back");
  var btnCancel       = document.getElementById("btn-cancel");
  var overlay         = document.getElementById("overlay");
  var overlaySuccess  = document.getElementById("overlay-success");
  var overlayMsg      = document.getElementById("overlay-message");

  packageCards.forEach(function (card) {
    card.addEventListener("click", function () {
      packageCards.forEach(function (c) { c.classList.remove("selected"); });
      card.classList.add("selected");
      selectedPackage = { id: card.dataset.id, price: card.dataset.price, name: card.dataset.name };
      selectedBanner.textContent = selectedPackage.name + " — KES " + selectedPackage.price;
      packagesSection.style.display = "none";
      paymentForm.style.display = "block";
      phoneInput.focus();
    });
  });

  btnBack.addEventListener("click", function () {
    paymentForm.style.display = "none";
    packagesSection.style.display = "block";
    phoneInput.value = "";
  });

  phoneInput.addEventListener("input", function () {
    this.value = this.value.replace(/\D/g, "").slice(0, 9);
  });

  btnPay.addEventListener("click", function () {
    var raw = phoneInput.value.trim();
    if (raw.length < 9) { phoneInput.focus(); return; }

    btnPay.disabled = true;
    btnPayText.textContent = "Sending…";
    btnPaySpinner.style.display = "inline-block";

    var phone = "254" + (raw.startsWith("0") ? raw.slice(1) : raw);

    fetch("/initiate-payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: phone, package_id: selectedPackage.id,
        client_mac: CLIENT_MAC, client_ip: CLIENT_IP,
        nds_token: NDS_TOKEN, redirect_url: REDIRECT_URL,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btnPay.disabled = false;
        btnPayText.textContent = "Pay Now";
        btnPaySpinner.style.display = "none";
        if (data.error) { alert(data.error); return; }
        currentSessionId = data.session_id;
        overlay.style.display = "flex";
        startPolling();
      })
      .catch(function () {
        btnPay.disabled = false;
        btnPayText.textContent = "Pay Now";
        btnPaySpinner.style.display = "none";
        alert("Network error. Please try again.");
      });
  });

  btnCancel.addEventListener("click", function () {
    stopPolling();
    overlay.style.display = "none";
    currentSessionId = null;
  });

  function startPolling() {
    var attempts = 0;
    pollInterval = setInterval(function () {
      attempts++;
      fetch("/check-payment/" + currentSessionId)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === "paid") {
            stopPolling();
            overlay.style.display = "none";
            overlaySuccess.style.display = "flex";
            setTimeout(function () {
              // Redirect through nodogsplash auth URL so the router unlocks this device.
              // The browser is on the local WiFi so it can reach the router directly.
              window.location.href = data.nds_auth_url || data.redirect_url || "https://google.com";
            }, 2000);
          } else if (data.status === "failed") {
            stopPolling();
            overlay.style.display = "none";
            alert("Payment was declined or cancelled. Please try again.");
          } else if (attempts >= 60) {
            stopPolling();
            overlay.style.display = "none";
            alert("Payment timed out. If you were charged, contact support.");
          }
        })
        .catch(function () {});
    }, 2000);
  }

  function stopPolling() {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  }
})();
