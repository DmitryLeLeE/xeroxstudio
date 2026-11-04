(function () {
  var L = localStorage.getItem("zine.lang") || ((navigator.language || "en").toLowerCase().indexOf("ru") === 0 ? "ru" : "en");
  function apply() {
    document.documentElement.lang = L;
    document.querySelectorAll("[data-ru]").forEach(function (e) { e.textContent = e.dataset[L]; });
    document.getElementById("lang").textContent = L === "ru" ? "EN" : "RU";
    document.title = L === "ru" ? "Xerox Zine Studio — ксерокс-зины из ваших фото" : "Xerox Zine Studio — make xerox zines from your photos";
  }
  document.getElementById("lang").addEventListener("click", function () { L = L === "ru" ? "en" : "ru"; try { localStorage.setItem("zine.lang", L); } catch (e) {} apply(); });
  apply();
  var pgs = document.querySelectorAll(".wall .pg");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }); }, { rootMargin: "0px 0px -8% 0px" });
    pgs.forEach(function (p) { io.observe(p); });
  } else { pgs.forEach(function (p) { p.classList.add("in"); }); }
})();
