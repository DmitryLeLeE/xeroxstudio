// Темы лендинга и гайда: те же четыре, что в приложении (usa, paper, dark, robot), общий ключ zine.theme.
(function () {
  var THEMES = [["usa", "★ USA"], ["paper", "Paper"], ["dark", "Dark"], ["robot", "Robot"]];
  var COLOR = { usa: "#081040", paper: "#f1ece0", dark: "#121212", robot: "#050605" };
  function read() {
    var t = "usa";
    try { t = JSON.parse(localStorage.getItem("zine.theme")) || "usa"; } catch (e) {}
    return COLOR[t] ? t : "usa";
  }
  function apply(t) {
    document.documentElement.setAttribute("data-theme", t);
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute("content", COLOR[t]);
  }
  apply(read());
  document.addEventListener("DOMContentLoaded", function () {
    var nav = document.querySelector(".nav nav");
    if (!nav || document.getElementById("theme")) return;
    var sel = document.createElement("select");
    sel.id = "theme"; sel.className = "chip theme-sel"; sel.setAttribute("aria-label", "Theme");
    THEMES.forEach(function (p) { var o = document.createElement("option"); o.value = p[0]; o.textContent = p[1]; sel.appendChild(o); });
    sel.value = read();
    sel.addEventListener("change", function () {
      apply(sel.value);
      try { localStorage.setItem("zine.theme", JSON.stringify(sel.value)); } catch (e) {}
    });
    nav.appendChild(sel);
  });
})();
