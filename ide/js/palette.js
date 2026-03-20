/* Palette editor - 32 colors, 3-3-2 RGB */

(function() {
  "use strict";

  var COLORS = 32;
  var palette = [];
  var selectedIndex = 0;

  /* 332 to hex */
  function toHex(v) {
    var r = (v >> 5) & 7;
    var g = (v >> 2) & 7;
    var b = v & 3;
    r = Math.round((r / 7) * 255);
    g = Math.round((g / 7) * 255);
    b = Math.round((b / 3) * 255);
    return "#" + [r,g,b].map(function(x) {
      var h = x.toString(16);
      return h.length === 1 ? "0" + h : h;
    }).join("");
  }

  /* RGB to 332 */
  function to332(r, g, b) {
    r = Math.min(7, Math.floor((r / 255) * 8));
    g = Math.min(7, Math.floor((g / 255) * 8));
    b = Math.min(3, Math.floor((b / 255) * 4));
    return (r << 5) | (g << 2) | b;
  }

  function initDefaultPalette() {
    /* Default Scramble-like palette from gfxdata.h */
    var raw = [
      0x00,0x80,0xf0,0xff,0x00,0xf0,0xc0,0x7f,
      0x00,0xc0,0x04,0x1f,0x00,0xd0,0xd0,0x0f,
      0x00,0xc0,0xc0,0x0f,0x00,0x04,0x04,0x0f,
      0x00,0xff,0x0f,0xf0,0x00,0x7f,0x0f,0xdf
    ];
    for (var i = 0; i < COLORS; i++) {
      palette[i] = raw[i] !== undefined ? raw[i] : 0;
    }
  }

  function updateColorPicker() {
    var v = palette[selectedIndex] || 0;
    var r = (v >> 5) & 7;
    var g = (v >> 2) & 7;
    var b = v & 3;
    var rEl = document.getElementById("pal-r");
    var gEl = document.getElementById("pal-g");
    var bEl = document.getElementById("pal-b");
    if (rEl) { rEl.value = r; document.getElementById("pal-r-val").textContent = r; }
    if (gEl) { gEl.value = g; document.getElementById("pal-g-val").textContent = g; }
    if (bEl) { bEl.value = b; document.getElementById("pal-b-val").textContent = b; }
    var prev = document.getElementById("color-preview");
    if (prev) prev.style.backgroundColor = toHex(v);
  }

  function updateFromSliders() {
    var r = parseInt(document.getElementById("pal-r").value, 10);
    var g = parseInt(document.getElementById("pal-g").value, 10);
    var b = parseInt(document.getElementById("pal-b").value, 10);
    palette[selectedIndex] = to332(
      Math.round((r / 7) * 255) || 0,
      Math.round((g / 7) * 255) || 0,
      Math.round((b / 3) * 255) || 0
    );
    updateColorPicker();
    redrawSwatches();
    if (window.IDE.graphics) window.IDE.graphics.refreshPalette();
  }

  function redrawSwatches() {
    var grid = document.getElementById("palette-grid");
    if (!grid) return;
    var swatches = grid.querySelectorAll(".pal-swatch");
    swatches.forEach(function(sw, i) {
      sw.style.backgroundColor = toHex(palette[i] || 0);
    });
  }

  window.IDE = window.IDE || {};

  window.IDE.palette = {
    init: function() {
      initDefaultPalette();
      var grid = document.getElementById("palette-grid");
      if (!grid) return;

      for (var i = 0; i < COLORS; i++) {
        var sw = document.createElement("div");
        sw.className = "pal-swatch" + (i === 0 ? " selected" : "");
        sw.style.backgroundColor = toHex(palette[i]);
        sw.dataset.index = i;
        sw.addEventListener("click", function() {
          selectedIndex = parseInt(this.dataset.index, 10);
          grid.querySelectorAll(".pal-swatch").forEach(function(s) { s.classList.remove("selected"); });
          this.classList.add("selected");
          updateColorPicker();
        });
        grid.appendChild(sw);
      }

      ["pal-r", "pal-g", "pal-b"].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener("input", updateFromSliders);
      });

      updateColorPicker();
    },

    getColors: function() {
      var out = [];
      for (var i = 0; i < COLORS; i++) out.push(toHex(palette[i] || 0));
      return out;
    },

    getRaw: function() {
      return palette.slice();
    },

    setRaw: function(arr) {
      for (var i = 0; i < COLORS && i < arr.length; i++) palette[i] = arr[i];
      redrawSwatches();
      updateColorPicker();
    },

    exportBytes: function() {
      return new Uint8Array(palette);
    }
  };
})();
