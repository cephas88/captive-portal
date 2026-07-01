(function () {
  "use strict";

  let selectedPackage = null;
  let currentSessionId = null;
  let pollInterval = null;

  const packageCards   = document.querySelectorAll(".package-card");
  const packagesSection = document.querySelector(".packages");
  const paymentForm    = document.getElementById("payment-form");
  const selectedBanner = document.getElementById("selected-pkg-banner");
  const phoneInput     = document.getElementById("phone");
  const btnPay         = document.getElementById("btn-pay");
  const btnPayText     = document.getElementById("btn-pay-text");
  const btnPaySpinner  = document.getElementById("btn-pay-spinner");
  const btnBack        = document.getElementById("btn-back");
  const btnCancel      = document.getElementById("btn-cancel");
  const overlay        = document.getElementById("overlay");
  const overlaySuccess = document.getElementById("overlay-success");
  const overlayMsg     = document.getElementById("overlay-message");

  // ── Package selection ──────────────────────────────────────────────────────

  packageCards.forEach(function (card) {
    card.addEventListener("click", function () {
      packageCards.forEach(function (c) { c.classList.remove("selected"); });
      card.classList.add("selected");

      selectedPackage = {
        id:    card.dataset.id,
        price: card.dataset.price,
        name:  card.dataset.name,
      };

      selectedBanner.textContent =
        selectedPackage.name + " — KES " + selectedPackage.price;

      packagesSection.style.display = "none";
      paymentForm.style.display = "block";
      phoneInput.focus();
    });
  });

  // ── Back button ────────────────────────────────────────────────────────────

  btnBack.addEventListener("click", function () {
    paymentForm.style.display = "none";
    packagesSection.style.display = "block";
    phoneInput.value = "";
  });

  // ── Phone number validation ────────────────────────────────────────────────

  phoneInput.addEventListener("input", function () {
    this.value = this.value.replace(/\D/g, "").slice(0, 9);
  });

  // ── Pay button ─────────────────────────────────────────────────────────────

  btnPay.addEventListener("click", function () {
    var raw = phoneInput.value.trim();

    if (raw.length < 9) {
      phoneInput.style.borderColor = "#d32f2f";
      phoneInput.focus();
      return;
    }
    phoneInput.style.borderColor = "";

    // Show spinner on button
    btnPay.disabled = true;
    btnPayText.textContent = "Sending…";
    btnPaySpinner.style.display = "inline-block";

    var phone = raw.startsWith("0") ? "254" + raw.slice(1) : "254" + raw;

    fetch("/initiate-payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone:        phone,
        package_id:   selectedPackage.id,
        client_mac:   CLIENT_MAC,
        client_ip:    CLIENT_IP,
        nds_token:    NDS_TOKEN,
        redirect_url: REDIRECT_URL,
      }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        btnPay.disabled = false;
        btnPayText.textContent = "Pay Now";
        btnPaySpinner.style.display = "none";

        if (data.error) {
          alert(data.error);
          return;
        }

        currentSessionId = data.session_id;
        showWaitingOverlay();
        startPolling();
      })
      .catch(function () {
        btnPay.disabled = false;
        btnPayText.textContent = "Pay Now";
        btnPaySpinner.style.display = "none";
        alert("Network error. Please try again.");
      });
  });

  // ── Waiting overlay ────────────────────────────────────────────────────────

  function showWaitingOverlay() {
    overlayMsg.textContent =
      "Enter your M-Pesa PIN on your phone to complete the payment.";
    overlay.style.display = "flex";
  }

  btnCancel.addEventListener("click", function () {
    stopPolling();
    overlay.style.display = "none";
    currentSessionId = null;
  });

  // ── Polling ────────────────────────────────────────────────────────────────

  function startPolling() {
    var attempts = 0;
    var maxAttempts = 60; // 2 minutes at 2s intervals

    pollInterval = setInterval(function () {
      attempts++;

      fetch("/check-payment/" + currentSessionId)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.status === "paid") {
            stopPolling();
            overlay.style.display = "none";
            overlaySuccess.style.display = "flex";
            setTimeout(function () {
              // nds_auth_url redirects through the router (on local WiFi)
              // to unlock this device, then on to the original destination.
              var target = data.nds_auth_url || data.redirect_url || "https://google.com";
              window.location.href = target;
            }, 2000);
          } else if (data.status === "failed") {
            stopPolling();
            overlay.style.display = "none";
            alert("Payment was declined or cancelled. Please try again.");
          } else if (attempts >= maxAttempts) {
            stopPolling();
            overlay.style.display = "none";
            overlayMsg.textContent =
              "Payment timed out. If you were charged, contact support.";
          }
        })
        .catch(function () {
          // Ignore transient network errors during polling
        });
    }, 2000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }
})();
