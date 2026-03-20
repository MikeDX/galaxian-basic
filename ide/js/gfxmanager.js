/* Graphics manager - load/save .gfx.json, parse gfxdata.h
 * JSON stores native format (tiles as 2D arrays). ROM conversion only on import/export.
 */

(function() {
  "use strict";

  function parseHexBytes(text) {
    var out = [];
    var re = /0x([0-9a-fA-F]{2})/g;
    var m;
    while ((m = re.exec(text)) !== null) out.push(parseInt(m[1], 16));
    return out;
  }

  function parseGfxdataH(text) {
    var palette = [], tiles = [];
    var palStart = text.indexOf("palette[32]");
    var tileromStart = text.indexOf("tilerom[0x1000]");
    if (palStart >= 0 && tileromStart > palStart) {
      var palChunk = text.substring(palStart, tileromStart);
      var palDataStart = palChunk.indexOf(" = {");
      if (palDataStart >= 0) palette = parseHexBytes(palChunk.substring(palDataStart));
      else palette = parseHexBytes(palChunk);
    }
    if (tileromStart >= 0) {
      var tileChunk = text.substring(tileromStart);
      var braceStart = tileChunk.indexOf(" = {");
      if (braceStart >= 0) tiles = parseHexBytes(tileChunk.substring(braceStart));
      else tiles = parseHexBytes(tileChunk);
    }
    return { palette: palette.slice(0, 32), tiles: tiles.slice(0, 4096) };
  }

  function bytesToBase64(bytes) {
    var binary = "";
    for (var i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  function base64ToBytes(b64) {
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  window.IDE = window.IDE || {};

  window.IDE.gfxmanager = {
    /* Load from .gfx.json - prefers native format, falls back to ROM base64 */
    loadFromJson: function(jsonText) {
      var data = JSON.parse(jsonText);
      var palette = (data.palette || []).slice(0, 32);
      while (palette.length < 32) palette.push(0);

      if (data.tiles && Array.isArray(data.tiles)) {
        return { palette: palette, nativeTiles: data.tiles };
      }
      var tilesB64 = data.tiles || "";
      var tilesBytes = tilesB64 ? base64ToBytes(tilesB64) : new Uint8Array(4096);
      return { palette: palette, tilesBytes: tilesBytes };
    },

    /* Save to .gfx.json - native format (human-friendly) */
    saveToJson: function() {
      var palette = window.IDE.palette ? window.IDE.palette.getRaw() : [];
      var nativeTiles = window.IDE.graphics ? window.IDE.graphics.exportNative() : [];
      return JSON.stringify({ palette: palette, tiles: nativeTiles }, null, 2);
    },

    /* Save to .gfx.json in ROM format (for build pipeline) */
    saveToJsonRom: function() {
      var palette = window.IDE.palette ? window.IDE.palette.getRaw() : [];
      var tilesBytes = window.IDE.graphics ? window.IDE.graphics.exportBytes() : new Uint8Array(4096);
      var tilesB64 = bytesToBase64(tilesBytes);
      return JSON.stringify({ palette: palette, tiles: tilesB64 }, null, 2);
    },

    parseGfxdataH: parseGfxdataH,

    /* Load from gfxdata.h - returns ROM bytes, graphics.loadFromBytes does the conversion */
    loadFromGfxdataH: function(text) {
      var parsed = parseGfxdataH(text);
      var tilesBytes = new Uint8Array(4096);
      for (var i = 0; i < parsed.tiles.length && i < 4096; i++) tilesBytes[i] = parsed.tiles[i];
      return { palette: parsed.palette, tilesBytes: tilesBytes };
    }
  };
})();
