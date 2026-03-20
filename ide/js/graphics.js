/* Graphics editor - native format tiles[tileIndex][y][x] = 0-3
 * Edit in screen space. ROM conversion only on import/export.
 */

(function() {
  "use strict";

  var TILE_COUNT = 64;
  var PLANE_SIZE = 2048;
  var tiles = [];
  var selectedTile = 0;
  var penColor = 0;
  var paletteBase = 0;
  var canvas, ctx, tileGridEl, charGridEl, penColorsEl, paletteSelectEl;

  /* ---- ROM format (Galaxian) - used only for import/export ---- */
  /* MAME scramble_spritelayout: 4 blocks [TL, TR, BL, BR], 8 bytes each */
  function planeByteIdx(x, y) {
    return (y & 7) + (x >= 8 ? 8 : 0) + (y >= 8 ? 16 : 0);
  }

  function decodeRomTile(bytes, tileIndex) {
    var p0Base = tileIndex * 32;
    var p1Base = PLANE_SIZE + tileIndex * 32;
    var px = [];
    for (var y = 0; y < 16; y++) {
      px[y] = [];
      for (var x = 0; x < 16; x++) {
        var bi = planeByteIdx(x, y);
        var bit = 7 - (x & 7);
        var p0 = (bytes[p0Base + bi] >> bit) & 1;
        var p1 = (bytes[p1Base + bi] >> bit) & 1;
        px[y][x] = p0 | (p1 << 1);
      }
    }
    return px;
  }

  function encodeRomTile(px) {
    var bytes = new Uint8Array(64);
    for (var y = 0; y < 16; y++) {
      for (var x = 0; x < 16; x++) {
        var p = px[y][x] & 3;
        var bi = planeByteIdx(x, y);
        var bit = 7 - (x & 7);
        if (p & 1) bytes[bi] |= 1 << bit;
        if (p & 2) bytes[32 + bi] |= 1 << bit;
      }
    }
    return bytes;
  }

  /* ---- Native format: decoded pixels, no transforms ---- */
  function initTilesFromDefault() {
    tiles = [];
    for (var t = 0; t < TILE_COUNT; t++) {
      var px = [];
      for (var y = 0; y < 16; y++) {
        px[y] = [];
        for (var x = 0; x < 16; x++) px[y][x] = 0;
      }
      tiles.push(px);
    }
  }

  function drawTileToCanvas(tileIndex) {
    if (!ctx || !tiles[tileIndex]) return;
    var px = tiles[tileIndex];
    var allColors = window.IDE.palette ? window.IDE.palette.getColors() : ["#000", "#f00", "#0f0", "#00f"];
    var palette = [allColors[paletteBase * 4], allColors[paletteBase * 4 + 1], allColors[paletteBase * 4 + 2], allColors[paletteBase * 4 + 3]];
    var scale = 8;
    ctx.save();
    ctx.translate(128, 0);
    ctx.rotate(Math.PI / 2);
    for (var y = 0; y < 16; y++) {
      for (var x = 0; x < 16; x++) {
        ctx.fillStyle = palette[px[y][x]] || "#000";
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }
    ctx.restore();
    ctx.strokeStyle = "rgba(255,255,255,0.3)";
    ctx.lineWidth = 1;
    for (var i = 1; i < 16; i++) {
      ctx.beginPath();
      ctx.moveTo(i * scale, 0);
      ctx.lineTo(i * scale, 128);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * scale);
      ctx.lineTo(128, i * scale);
      ctx.stroke();
    }
    ctx.strokeStyle = "rgba(255,255,255,0.6)";
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, 64, 64);
    ctx.strokeRect(64, 0, 64, 64);
    ctx.strokeRect(0, 64, 64, 64);
    ctx.strokeRect(64, 64, 64, 64);
    ctx.strokeRect(0, 0, 128, 128);
  }

  function drawTileToThumb(px) {
    var c = document.createElement("canvas");
    c.width = c.height = 16;
    var tctx = c.getContext("2d");
    var allColors = window.IDE.palette ? window.IDE.palette.getColors() : ["#000", "#f00", "#0f0", "#00f"];
    var palette = [allColors[paletteBase * 4], allColors[paletteBase * 4 + 1], allColors[paletteBase * 4 + 2], allColors[paletteBase * 4 + 3]];
    tctx.translate(16, 0);
    tctx.rotate(Math.PI / 2);
    for (var y = 0; y < 16; y++)
      for (var x = 0; x < 16; x++) {
        tctx.fillStyle = palette[px[y][x]] || "#000";
        tctx.fillRect(x, y, 1, 1);
      }
    return c;
  }

  function redrawAll() {
    drawTileToCanvas(selectedTile);
    redrawThumbnails();
    redrawCharThumbnails();
  }

  function redrawThumbnails() {
    if (!tileGridEl) return;
    var thumbs = tileGridEl.querySelectorAll(".tile-thumb");
    thumbs.forEach(function(th, i) {
      if (!tiles[i]) return;
      var c = drawTileToThumb(tiles[i]);
      th.style.backgroundImage = "url(" + c.toDataURL() + ")";
      th.style.backgroundSize = "32px 32px";
      th.style.backgroundRepeat = "no-repeat";
      th.style.backgroundPosition = "center";
    });
  }

  function draw8x8Char(px, quadrant) {
    var c = document.createElement("canvas");
    c.width = c.height = 8;
    var tctx = c.getContext("2d");
    var allColors = window.IDE.palette ? window.IDE.palette.getColors() : ["#000", "#f00", "#0f0", "#00f"];
    var palette = [allColors[paletteBase * 4], allColors[paletteBase * 4 + 1], allColors[paletteBase * 4 + 2], allColors[paletteBase * 4 + 3]];
    tctx.translate(8, 0);
    tctx.rotate(Math.PI / 2);
    var xOfs = (quadrant & 1) ? 8 : 0;
    var yOfs = (quadrant & 2) ? 8 : 0;
    for (var y = 0; y < 8; y++)
      for (var x = 0; x < 8; x++) {
        tctx.fillStyle = palette[px[yOfs + y][xOfs + x]] || "#000";
        tctx.fillRect(x, y, 1, 1);
      }
    return c;
  }

  function rebuildTileGrid() {
    if (!tileGridEl) return;
    tileGridEl.innerHTML = "";
    for (var t = 0; t < TILE_COUNT; t++) {
      var th = document.createElement("div");
      th.className = "tile-thumb" + (t === 0 ? " selected" : "");
      th.dataset.index = t;
      th.addEventListener("click", function() {
        selectedTile = parseInt(this.dataset.index, 10);
        tileGridEl.querySelectorAll(".tile-thumb").forEach(function(el) { el.classList.remove("selected"); });
        charGridEl.querySelectorAll(".char-thumb").forEach(function(el) { el.classList.remove("selected"); });
        this.classList.add("selected");
        document.getElementById("tile-index").textContent = selectedTile;
        drawTileToCanvas(selectedTile);
      });
      tileGridEl.appendChild(th);
    }
    redrawThumbnails();
  }

  function rebuildCharGrid() {
    if (!charGridEl) return;
    charGridEl.innerHTML = "";
    for (var t = 0; t < TILE_COUNT; t++) {
      for (var q = 0; q < 4; q++) {
        var ch = document.createElement("div");
        ch.className = "char-thumb";
        ch.dataset.tile = t;
        ch.dataset.quad = q;
        ch.addEventListener("click", function() {
          selectedTile = parseInt(this.dataset.tile, 10);
          tileGridEl.querySelectorAll(".tile-thumb").forEach(function(el) { el.classList.remove("selected"); });
          charGridEl.querySelectorAll(".char-thumb").forEach(function(el) { el.classList.remove("selected"); });
          this.classList.add("selected");
          document.getElementById("tile-index").textContent = selectedTile;
          drawTileToCanvas(selectedTile);
        });
        charGridEl.appendChild(ch);
      }
    }
    redrawCharThumbnails();
  }

  function redrawCharThumbnails() {
    if (!charGridEl) return;
    var chars = charGridEl.querySelectorAll(".char-thumb");
    chars.forEach(function(ch) {
      var t = parseInt(ch.dataset.tile, 10);
      var q = parseInt(ch.dataset.quad, 10);
      if (!tiles[t]) return;
      var c = draw8x8Char(tiles[t], q);
      ch.style.backgroundImage = "url(" + c.toDataURL() + ")";
      ch.style.backgroundSize = "16px 16px";
      ch.style.backgroundRepeat = "no-repeat";
      ch.style.backgroundPosition = "center";
    });
  }

  window.IDE = window.IDE || {};

  window.IDE.graphics = {
    init: function() {
      canvas = document.getElementById("tile-canvas");
      tileGridEl = document.getElementById("tile-grid");
      charGridEl = document.getElementById("char-grid");
      penColorsEl = document.getElementById("pen-colors");
      paletteSelectEl = document.getElementById("gfx-palette-select");
      if (!canvas || !tileGridEl) return;

      ctx = canvas.getContext("2d");
      initTilesFromDefault();

      var allColors = window.IDE.palette ? window.IDE.palette.getColors() : ["#000", "#f00", "#0f0", "#00f"];
      function updatePenSwatches() {
        penColorsEl.innerHTML = "";
        for (var i = 0; i < 4; i++) {
          var sw = document.createElement("div");
          sw.className = "pen-swatch" + (i === penColor ? " selected" : "");
          sw.style.backgroundColor = allColors[paletteBase * 4 + i] || "#000";
          sw.dataset.color = i;
          sw.addEventListener("click", function() {
            penColor = parseInt(this.dataset.color, 10);
            penColorsEl.querySelectorAll(".pen-swatch").forEach(function(s) { s.classList.remove("selected"); });
            this.classList.add("selected");
          });
          penColorsEl.appendChild(sw);
        }
      }
      updatePenSwatches();

      if (paletteSelectEl) {
        paletteSelectEl.addEventListener("change", function() {
          paletteBase = parseInt(this.value, 10) || 0;
          updatePenSwatches();
          redrawAll();
        });
      }

      rebuildTileGrid();
      rebuildCharGrid();

      var scale = 8;
      function screenToTile(sx, sy) {
        var r = canvas.getBoundingClientRect();
        var cx = (sx - r.left) * (128 / r.width);
        var cy = (sy - r.top) * (128 / r.height);
        if (cx < 0 || cx >= 128 || cy < 0 || cy >= 128) return null;
        var tx = Math.floor(cy / scale);
        var ty = Math.floor((127 - cx) / scale);
        return { x: tx, y: ty };
      }
      canvas.addEventListener("mousedown", function(e) {
        var pt = screenToTile(e.clientX, e.clientY);
        if (pt && tiles[selectedTile]) {
          tiles[selectedTile][pt.y][pt.x] = penColor;
          drawTileToCanvas(selectedTile);
          redrawThumbnails();
          redrawCharThumbnails();
        }
        var move = function(ev) {
          var pt = screenToTile(ev.clientX, ev.clientY);
          if (pt && tiles[selectedTile]) {
            tiles[selectedTile][pt.y][pt.x] = penColor;
            drawTileToCanvas(selectedTile);
            redrawThumbnails();
            redrawCharThumbnails();
          }
        };
        var up = function() {
          document.removeEventListener("mousemove", move);
          document.removeEventListener("mouseup", up);
        };
        document.addEventListener("mousemove", move);
        document.addEventListener("mouseup", up);
      });

      document.getElementById("btn-clear-tile").addEventListener("click", function() {
        if (!tiles[selectedTile]) return;
        for (var y = 0; y < 16; y++)
          for (var x = 0; x < 16; x++) tiles[selectedTile][y][x] = 0;
        drawTileToCanvas(selectedTile);
        redrawThumbnails();
        redrawCharThumbnails();
      });

      redrawAll();
    },

    getTiles: function() { return tiles; },
    setTiles: function(arr) { tiles = arr || []; redrawAll(); },

    /* Export: tiles -> ROM bytes */
    exportBytes: function() {
      var out = new Uint8Array(4096);
      for (var t = 0; t < TILE_COUNT; t++) {
        if (!tiles[t]) continue;
        var enc = encodeRomTile(tiles[t]);
        for (var i = 0; i < 32; i++) out[t * 32 + i] = enc[i];
        for (var i = 0; i < 32; i++) out[PLANE_SIZE + t * 32 + i] = enc[32 + i];
      }
      return out;
    },

    /* Import: ROM bytes -> tiles (decode only, no transform) */
    loadFromBytes: function(bytes) {
      if (!bytes || bytes.length < 4096) {
        initTilesFromDefault();
      } else {
        tiles = [];
        for (var t = 0; t < TILE_COUNT; t++) {
          tiles[t] = decodeRomTile(bytes, t);
        }
      }
      rebuildTileGrid();
      redrawAll();
    },

    /* Import from JSON tiles array (same format as we store) */
    loadFromNative: function(nativeTiles) {
      tiles = [];
      for (var t = 0; t < TILE_COUNT; t++) {
        var src = nativeTiles[t];
        var px = [];
        for (var y = 0; y < 16; y++) {
          px[y] = [];
          for (var x = 0; x < 16; x++) px[y][x] = (src && src[y] && (src[y][x] & 3)) || 0;
        }
        tiles.push(px);
      }
      rebuildTileGrid();
      redrawAll();
    },

    /* Export native format for JSON */
    exportNative: function() {
      return tiles.map(function(t) {
        return t.map(function(row) { return row.slice(); });
      });
    },

    refreshPalette: function() {
      var allColors = window.IDE.palette ? window.IDE.palette.getColors() : ["#000", "#f00", "#0f0", "#00f"];
      penColorsEl.querySelectorAll(".pen-swatch").forEach(function(sw, i) {
        sw.style.backgroundColor = allColors[paletteBase * 4 + i] || "#000";
      });
      redrawAll();
    },

    setPaletteBase: function(base) {
      paletteBase = base || 0;
      if (paletteSelectEl) paletteSelectEl.value = paletteBase;
      this.refreshPalette();
    }
  };
})();
