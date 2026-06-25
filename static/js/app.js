const form = document.getElementById("analyze-form");
const analyzeBtn = document.getElementById("analyze-btn");
const errorMsg = document.getElementById("error-msg");

const frontInput = document.getElementById("front-photo");
const sideInput = document.getElementById("side-photo");
const frontPreview = document.getElementById("front-preview");
const sidePreview = document.getElementById("side-preview");
const frontCard = document.getElementById("front-card");
const sideCard = document.getElementById("side-card");

const genderInput = document.getElementById("gender");
const sexButtons = document.querySelectorAll(".sex-btn");

function setupPreview(input, preview, card) {
  if (!input || !preview || !card) return;
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    card.classList.remove("has-example");
    card.classList.add("has-image");
  });
}

setupPreview(frontInput, frontPreview, frontCard);
setupPreview(sideInput, sidePreview, sideCard);

function initFloatingLogos() {
  const logo = document.getElementById("bg-logo");
  const float = logo?.querySelector(".bg-logo-float");
  if (!logo || !float) return;

  const LOGO_W = 128;
  const PAGE_W = 1280;
  const yMin = 6;
  const yMax = 78;

  let side = Math.random() < 0.5 ? "left" : "right";
  let x = 0;
  let y = 14 + Math.random() * 50;
  let vx = 0;
  let vy = 0;
  let hovering = false;

  function margins() {
    const vw = window.innerWidth;
    const pad = 8;
    const contentLeft = Math.max(pad, (vw - Math.min(PAGE_W, vw)) / 2);
    const contentRight = contentLeft + Math.min(PAGE_W, vw - contentLeft * 2);
    const leftMax = Math.max(pad, contentLeft - LOGO_W - pad);
    const rightMin = contentRight + pad;
    const rightMax = Math.max(rightMin, vw - LOGO_W - pad);
    return { pad, leftMax, rightMin, rightMax };
  }

  function randomXForSide(nextSide) {
    const { pad, leftMax, rightMin, rightMax } = margins();
    if (nextSide === "left") {
      return pad + Math.random() * Math.max(0, leftMax - pad);
    }
    return rightMin + Math.random() * Math.max(0, rightMax - rightMin);
  }

  function boundsForSide(activeSide) {
    const { pad, leftMax, rightMin, rightMax } = margins();
    if (activeSide === "left") {
      return { xMin: pad, xMax: leftMax };
    }
    return { xMin: rightMin, xMax: rightMax };
  }

  function nudgeVelocity() {
    vx += (Math.random() - 0.5) * 0.9;
    vy += (Math.random() - 0.5) * 0.4;
    vx = Math.max(-1.9, Math.min(1.9, vx));
    vy = Math.max(-0.8, Math.min(0.8, vy));
  }

  function switchSide() {
    side = side === "left" ? "right" : "left";
    x = randomXForSide(side);
    vx = (Math.random() - 0.5) * 1.4;
    vy = (Math.random() - 0.5) * 0.65;
  }

  x = randomXForSide(side);
  nudgeVelocity();
  window.setInterval(nudgeVelocity, 1100 + Math.random() * 1200);
  window.setInterval(() => {
    if (Math.random() < 0.45) switchSide();
  }, 3200 + Math.random() * 2000);

  logo.addEventListener("mouseenter", () => { hovering = true; });
  logo.addEventListener("mouseleave", () => { hovering = false; });

  const tick = () => {
    if (!hovering) {
      const { xMin, xMax } = boundsForSide(side);
      x += vx;
      y += vy;

      if (x <= xMin || x >= xMax) {
        vx *= -1;
        x = Math.max(xMin, Math.min(xMax, x));
        nudgeVelocity();
        if (Math.random() < 0.35) switchSide();
      }
      if (y <= yMin || y >= yMax) {
        vy *= -1;
        y = Math.max(yMin, Math.min(yMax, y));
        nudgeVelocity();
      }
      if (Math.random() < 0.012) nudgeVelocity();

      float.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(2)}vh, 0)`;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initFloatingLogos);
} else {
  initFloatingLogos();
}

sexButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    sexButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    genderInput.value = btn.dataset.gender;
  });
});

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.hidden = !msg;
}

function highlightRange(key) {
  document.querySelectorAll(".range-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.key === key);
  });
}

function setBadge(category, key) {
  const badge = document.getElementById("res-badge");
  badge.textContent = `✓ ${category} range`;
  badge.className = "result-badge";
  if (key !== "fitness") badge.classList.add(key);
  badge.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");

  const frontFile = frontInput.files?.[0];
  const sideFile = sideInput.files?.[0];
  if (!frontFile || !sideFile) {
    showError("Please upload both front and side photos.");
    return;
  }

  const body = new FormData();
  body.append("front_photo", frontFile);
  body.append("side_photo", sideFile);
  body.append("weight_kg", document.getElementById("weight").value);
  body.append("height_feet", document.getElementById("height-feet").value);
  body.append("height_inches", document.getElementById("height-inches").value || "0");
  body.append("gender", genderInput.value);

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span class="spark">◌</span> Analyzing…';

  try {
    const res = await fetch("/api/analyze", { method: "POST", body });
    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error(
        res.status === 0 || !res.ok
          ? "Cannot reach the analysis server. Please try again in a moment."
          : "Invalid server response",
      );
    }

    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
        : detail || "Analysis failed";
      throw new Error(msg);
    }

    document.getElementById("res-bf").textContent = `${data.body_fat_pct}%`;
    document.getElementById("res-lean").textContent = `${data.lean_mass_kg} kg`;
    document.getElementById("res-fat").textContent = `${data.fat_mass_kg} kg`;
    document.getElementById("res-bmi").textContent = data.bmi;

    setBadge(data.category, data.category_key);
    highlightRange(data.category_key);
  } catch (err) {
    const msg = err.message || String(err);
    if (msg === "Failed to fetch" || msg.includes("NetworkError") || msg.includes("Load failed")) {
      showError("Unable to connect to the server. Check your connection and try again.");
    } else {
      showError(msg);
    }
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '<span class="spark">✦</span> Analyze body composition';
  }
});
