/**
 * Payment form validation for checkout flow.
 * Handles credit card validation and multi-step checkout process.
 */

const PaymentValidator = (() => {
  // Validation functions
  function validateCardNumber(cardNum) {
    if (!cardNum) return "Card number is required";
    const cleaned = cardNum.replace(/[\s\-]/g, "");
    if (!/^\d{13,19}$/.test(cleaned)) {
      return "Card number must be 13-19 digits";
    }
    return null; // valid
  }

  function validateExpiry(expiry) {
    if (!expiry) return "Expiry date is required";
    if (!/^\d{2}\/\d{2}$/.test(expiry)) {
      return "Expiry must be in MM/YY format";
    }
    const [month, year] = expiry.split("/");
    const m = parseInt(month, 10);
    const y = parseInt(year, 10);

    if (m < 1 || m > 12) {
      return "Month must be 01-12";
    }

    // Check if expired
    const now = new Date();
    const currentYear = now.getFullYear() % 100; // 2-digit year
    const currentMonth = now.getMonth() + 1; // 1-12

    if (y < currentYear || (y === currentYear && m < currentMonth)) {
      return "Card has expired";
    }

    return null; // valid
  }

  function validateCVV(cvv) {
    if (!cvv) return "CVV is required";
    if (!/^\d{3,4}$/.test(cvv)) {
      return "CVV must be 3-4 digits";
    }
    return null; // valid
  }

  function validateAllFields() {
    const cardNum = document.getElementById("input-card-number").value;
    const expiry = document.getElementById("input-card-expiry").value;
    const cvv = document.getElementById("input-card-cvv").value;

    const cardErr = validateCardNumber(cardNum);
    const expiryErr = validateExpiry(expiry);
    const cvvErr = validateCVV(cvv);

    if (cardErr || expiryErr || cvvErr) {
      return cardErr || expiryErr || cvvErr;
    }

    return null; // all valid
  }

  // UI functions
  function showCardForm() {
    document.getElementById("step1-method").classList.add("d-none");
    document.getElementById("step2-payment").classList.remove("d-none");
  }

  function hideCardForm() {
    document.getElementById("step1-method").classList.remove("d-none");
    document.getElementById("step2-payment").classList.add("d-none");
    clearCardFormErrors();
  }

  function showError(message) {
    const errEl = document.getElementById("card-form-error");
    if (errEl) {
      errEl.textContent = message;
      errEl.classList.remove("d-none");
    }
  }

  function clearCardFormErrors() {
    const errEl = document.getElementById("card-form-error");
    if (errEl) errEl.classList.add("d-none");
  }

  return {
    validateCardNumber,
    validateExpiry,
    validateCVV,
    validateAllFields,
    showCardForm,
    hideCardForm,
    showError,
    clearCardFormErrors,
  };
})();
