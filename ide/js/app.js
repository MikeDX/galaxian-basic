/* Main app - tabs, toolbar, init */

(function() {
  "use strict";

  function initTabs() {
    document.querySelectorAll(".tab").forEach(function(tab) {
      tab.addEventListener("click", function() {
        var name = this.dataset.tab;
        document.querySelectorAll(".tab").forEach(function(t) { t.classList.remove("active"); });
        document.querySelectorAll(".panel").forEach(function(p) { p.classList.remove("active"); });
        this.classList.add("active");
        var panel = document.getElementById("panel-" + name);
        if (panel) panel.classList.add("active");
      });
    });
  }

  function initToolbar() {
    var status = document.getElementById("status");
    function setStatus(msg) {
      if (status) status.textContent = msg;
    }

    document.getElementById("btn-new")?.addEventListener("click", function() {
      if (window.IDE.editor) window.IDE.editor.setValue("10 REM New program\n20 CLS\n30 GOTO 30\n");
      setStatus("New file");
    });

    document.getElementById("btn-open")?.addEventListener("click", function() {
      var inp = document.createElement("input");
      inp.type = "file";
      inp.accept = ".bas";
      inp.onchange = function() {
        var f = inp.files[0];
        if (!f) return;
        var r = new FileReader();
        r.onload = function() {
          if (window.IDE.editor) window.IDE.editor.setValue(r.result);
          setStatus("Opened " + f.name);
          var gfxPath = f.name.replace(/\.bas$/, ".gfx.json");
          setStatus("Opened " + f.name);
        };
        r.readAsText(f);
      };
      inp.click();
    });

    document.getElementById("btn-save")?.addEventListener("click", function() {
      var code = window.IDE.editor ? window.IDE.editor.getValue() : "";
      var a = document.createElement("a");
      a.href = "data:text/plain;charset=utf-8," + encodeURIComponent(code);
      a.download = "program.bas";
      a.click();
      setStatus("Saved program.bas");
    });

    document.getElementById("btn-build")?.addEventListener("click", function() {
      setStatus("Build: run 'make' from project root with your .bas file");
    });

    function loadGraphicsFile(file) {
      var r = new FileReader();
      r.onload = function() {
        var text = r.result;
        var data;
        if (file.name.endsWith(".gfx.json") || (file.name.endsWith(".json") && text.trim().startsWith("{"))) {
          data = window.IDE.gfxmanager.loadFromJson(text);
        } else if (file.name.endsWith(".h") || file.name.endsWith(".c")) {
          data = window.IDE.gfxmanager.loadFromGfxdataH(text);
        } else {
          setStatus("Unknown format - use .gfx.json or gfxdata.h");
          return;
        }
        if (window.IDE.palette) window.IDE.palette.setRaw(data.palette);
        if (window.IDE.graphics) {
          if (data.nativeTiles) window.IDE.graphics.loadFromNative(data.nativeTiles);
          else window.IDE.graphics.loadFromBytes(data.tilesBytes);
        }
        setStatus("Loaded " + file.name);
      };
      r.readAsText(file);
    }

    function doLoadGfx() {
      var inp = document.createElement("input");
      inp.type = "file";
      inp.accept = "*/*";  /* Allow all - some browsers block .gfx.json */
      inp.onchange = function() {
        var f = inp.files[0];
        if (f) loadGraphicsFile(f);
      };
      inp.click();
    }

    function doSaveGfx() {
      var json = window.IDE.gfxmanager ? window.IDE.gfxmanager.saveToJson() : "{}";
      var a = document.createElement("a");
      a.href = "data:application/json;charset=utf-8," + encodeURIComponent(json);
      a.download = "graphics.gfx.json";
      a.click();
      setStatus("Saved graphics.gfx.json");
    }

    document.getElementById("btn-load-gfx")?.addEventListener("click", doLoadGfx);
    document.getElementById("btn-save-gfx")?.addEventListener("click", doSaveGfx);
    document.getElementById("btn-load-gfx-panel")?.addEventListener("click", doLoadGfx);
    document.getElementById("btn-save-gfx-panel")?.addEventListener("click", doSaveGfx);
  }

  function init() {
    var defaultCode = "10 REM Galaxian BASIC\n20 CLS\n30 PRINT 8, 10, \"HELLO\"\n40 GOTO 40\n";
    if (window.IDE.editor) window.IDE.editor.init(defaultCode);
    if (window.IDE.help) window.IDE.help.init();
    if (window.IDE.palette) window.IDE.palette.init();
    if (window.IDE.graphics) window.IDE.graphics.init();
    initTabs();
    initToolbar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
