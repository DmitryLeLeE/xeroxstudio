// Применяет тему до отрисовки, чтобы не было вспышки. По умолчанию бумажная.
(function () {
  var t = "paper";
  try { t = JSON.parse(localStorage.getItem("zine.theme")) || "paper"; } catch (e) {}
  if (t !== "dark") t = "paper";
  document.documentElement.setAttribute("data-theme", t);
  var m = document.querySelector('meta[name="theme-color"]');
  if (m) m.setAttribute("content", t === "paper" ? "#f1ece0" : "#121212");
})();
