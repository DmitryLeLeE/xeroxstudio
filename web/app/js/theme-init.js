// Применяет тему до отрисовки, чтобы не было вспышки. По умолчанию «Америка × терминал» (usa).
(function () {
  var t = "usa";
  try { t = JSON.parse(localStorage.getItem("zine.theme")) || "usa"; } catch (e) {}
  if (t !== "dark" && t !== "paper" && t !== "robot") t = "usa";
  document.documentElement.setAttribute("data-theme", t);
  var m = document.querySelector('meta[name="theme-color"]');
  if (m) m.setAttribute("content", t === "paper" ? "#f1ece0" : t === "usa" ? "#081040" : t === "robot" ? "#050605" : "#121212");
})();
