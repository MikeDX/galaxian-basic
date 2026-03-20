/* Help system - Galaxian BASIC reference */

(function() {
  "use strict";

  var REFERENCE = [
    { id: "overview", title: "Overview", content: `
<h2>Overview</h2>
<p>Galaxian BASIC compiles to native Z80 code for Galaxian/Scramble arcade hardware.
Display: 224×256 pixels, 32×32 tiles, 32 colors.</p>
<p><strong>Pipeline:</strong> BASIC → C (gbasic.py) → Z80 (SDCC) → ROM</p>
` },
    { id: "display", title: "Display", content: `
<h2>Display commands</h2>
<dl>
<dt><code>CLS</code></dt><dd>Clear screen</dd>
<dt><code>PRINT x, y, "text"</code></dt><dd>Draw text at (x,y). x,y are tile coordinates 0-31.</dd>
<dt><code>POKE x, y, ch</code></dt><dd>Write char to VRAM at (x,y). Supports expressions.</dd>
<dt><code>COLOR col, attr</code></dt><dd>Set column color attribute</dd>
<dt><code>SCROLL col, val</code></dt><dd>Set column scroll (variable or literal)</dd>
<dt><code>PUTSHAPE x, y, ofs</code></dt><dd>2×2 tile block</dd>
<dt><code>FILL x, y, w, h, ch</code></dt><dd>Fill rectangle with char</dd>
</dl>
` },
    { id: "sprites", title: "Sprites", content: `
<h2>Sprites</h2>
<dl>
<dt><code>SPRITE n, x, y, code, color</code></dt><dd>Set sprite n (0-7). x,y in pixels.</dd>
<dt><code>HIDE n</code></dt><dd>Hide sprite n</dd>
<dt><code>MISSILE n, x, y</code></dt><dd>Hardware missile layer (8 missiles)</dd>
</dl>
` },
    { id: "input", title: "Input", content: `
<h2>Input</h2>
<dl>
<dt><code>JOY(n)</code></dt><dd>Joystick: 0=left, 1=right, 2=up, 3=down. Returns 1 if pressed.</dd>
<dt><code>INPUT(n)</code></dt><dd>0-3: P1 L/R/U/D, 4=Fire, 5=Bomb, 6=Coin, 7=Start, 8-11: P2, etc.</dd>
</dl>
` },
    { id: "control", title: "Control flow", content: `
<h2>Control flow</h2>
<dl>
<dt><code>GOTO n</code></dt><dd>Jump to line</dd>
<dt><code>GOSUB n</code> / <code>RETURN</code></dt><dd>Subroutine</dd>
<dt><code>IF expr THEN</code> ... <code>ELSE</code> ... <code>ENDIF</code></dt><dd>Block form</dd>
<dt><code>IF var op num THEN GOTO n</code></dt><dd>Conditional jump</dd>
<dt><code>FOR var = start TO end</code> ... <code>NEXT var</code></dt><dd>Loop</dd>
<dt><code>WAIT n</code></dt><dd>Wait n frames</dd>
<dt><code>LET var = expr</code></dt><dd>Assignment</dd>
</dl>
` },
    { id: "expressions", title: "Expressions", content: `
<h2>Expressions</h2>
<p>Arithmetic: <code>+</code> <code>-</code> <code>*</code> <code>/</code></p>
<p>Modulo: <code>MOD</code> (e.g. <code>X MOD 10</code>)</p>
<p>Bitwise: <code>AND</code>, <code>OR</code></p>
<p>Comparisons: <code>=</code> <code>&lt;&gt;</code> <code>&lt;</code> <code>&gt;</code> <code>&lt;=</code> <code>&gt;=</code></p>
<p>Variables: A-Z, A0-A9 style</p>
` },
    { id: "tiles", title: "Tile & charset", content: `
<h2>Tile & charset</h2>
<p>64 tiles, 16×16 px, 2 bpp (4 colors per tile).</p>
<p>Chars 0-9: digits. 0x10: space. A-Z: 0x11-0x2A.</p>
<p>Edit tiles in the Graphics tab.</p>
` }
  ];

  window.IDE = window.IDE || {};

  window.IDE.help = {
    init: function() {
      var nav = document.getElementById("help-nav");
      var content = document.getElementById("help-content");
      if (!nav || !content) return;

      REFERENCE.forEach(function(item, i) {
        var li = document.createElement("li");
        li.textContent = item.title;
        li.dataset.id = item.id;
        if (i === 0) li.classList.add("active");
        li.addEventListener("click", function() {
          nav.querySelectorAll("li").forEach(function(l) { l.classList.remove("active"); });
          li.classList.add("active");
          content.innerHTML = item.content;
        });
        nav.appendChild(li);
      });

      content.innerHTML = REFERENCE[0].content;
    }
  };
})();
