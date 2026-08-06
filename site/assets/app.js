const navToggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");

navToggle?.addEventListener("click", () => {
  const open = nav.dataset.open !== "true";
  nav.dataset.open = String(open);
  navToggle.setAttribute("aria-expanded", String(open));
});

nav?.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    nav.dataset.open = "false";
    navToggle?.setAttribute("aria-expanded", "false");
  }
});

document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});

const legacySections = {
  "/about/": "#about",
  "/team/": "#team",
  "/contact-us/": "#contact",
  "/what-we-do/": "#services",
  "/why-choose-us/": "#approach",
  "/our-strategy/": "#approach",
  "/engineered-software-solutions/": "#services",
  "/complex-system-integration/": "#services",
  "/our-project/": "#experience",
  "/aurizon/": "#experience",
  "/boeing/": "#experience",
  "/caterpillar/": "#experience",
  "/ashley-fletcher/": "#team"
};

const legacyTarget = legacySections[window.location.pathname];
if (legacyTarget) {
  history.replaceState(null, "", `/${legacyTarget}`);
  requestAnimationFrame(() => document.querySelector(legacyTarget)?.scrollIntoView());
}

const form = document.querySelector("[data-contact-form]");
if (form) {
  form.elements.startedAt.value = String(Date.now());
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector("[data-form-status]");
    const submit = form.querySelector("button[type='submit']");
    status.textContent = "Sending…";
    status.dataset.state = "pending";
    submit.disabled = true;

    const values = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.message || "Message could not be sent.");
      form.reset();
      form.elements.startedAt.value = String(Date.now());
      status.textContent = "Thanks — your message has been sent.";
      status.dataset.state = "success";
    } catch (error) {
      status.textContent = error.message || "Message could not be sent. Please try again later.";
      status.dataset.state = "error";
    } finally {
      submit.disabled = false;
    }
  });
}
