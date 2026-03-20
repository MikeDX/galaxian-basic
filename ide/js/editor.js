/* Code editor - CodeMirror with Galaxian BASIC mode */

(function() {
  "use strict";

  var editor;

  window.IDE = window.IDE || {};

  window.IDE.editor = {
    init: function(initialCode) {
      var container = document.getElementById("editor");
      if (!container) return;

      editor = CodeMirror(container, {
        value: initialCode || "10 REM Galaxian BASIC\n20 CLS\n30 PRINT 8, 10, \"HELLO\"\n40 GOTO 40\n",
        mode: "galaxian-basic",
        lineNumbers: true,
        indentUnit: 2,
        tabSize: 2,
        indentWithTabs: false,
        theme: "ambiance",
        autoCloseBrackets: false
      });

      return editor;
    },

    getValue: function() {
      return editor ? editor.getValue() : "";
    },

    setValue: function(code) {
      if (editor) editor.setValue(code);
    },

    focus: function() {
      if (editor) editor.focus();
    },

    getEditor: function() {
      return editor;
    }
  };
})();
