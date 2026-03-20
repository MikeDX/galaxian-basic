/* Galaxian BASIC syntax mode for CodeMirror 5 */
(function() {
  var CodeMirror = window.CodeMirror;
  if (!CodeMirror) return;
  "use strict";

  CodeMirror.defineMode("galaxian-basic", function() {
    var keywords = [
      "REM", "LET", "IF", "THEN", "ELSE", "ENDIF", "GOTO", "GOSUB", "RETURN",
      "FOR", "TO", "NEXT", "END",
      "CLS", "PRINT", "POKE", "COLOR", "SCROLL", "PUTSHAPE", "FILL",
      "SPRITE", "HIDE", "MISSILE",
      "WAIT", "JOY", "INPUT"
    ];
    var keywordSet = {};
    for (var i = 0; i < keywords.length; i++) keywordSet[keywords[i]] = true;

    function tokenBase(stream, state) {
      var ch = stream.next();
      if (ch == '"') {
        state.tokenize = tokenString;
        return state.tokenize(stream, state);
      }
      if (ch == "'" && stream.peek() != "'") {
        state.tokenize = tokenString;
        return state.tokenize(stream, state);
      }
      if (ch == "0" && stream.peek() && /[xX]/.test(stream.peek())) {
        stream.next();
        stream.eatWhile(/[0-9a-fA-F]/);
        return "number";
      }
      if (/\d/.test(ch)) {
        stream.eatWhile(/\d/);
        if (/[0-9a-fA-F]/.test(stream.peek())) {
          stream.eatWhile(/[0-9a-fA-F]/);
          if (/[hH]/.test(stream.peek())) stream.next();
        }
        return "number";
      }
      if (/[a-zA-Z_]/.test(ch)) {
        stream.eatWhile(/[\w]/);
        var word = stream.current().toUpperCase();
        if (keywordSet.hasOwnProperty(word)) return "keyword";
        return "variable";
      }
      return null;
    }

    function tokenString(stream, state) {
      var escaped = false, next;
      while ((next = stream.next()) != null) {
        if (next == '"' && !escaped) {
          state.tokenize = tokenBase;
          break;
        }
        escaped = !escaped && next == "\\";
      }
      return "string";
    }

    return {
      startState: function() { return { tokenize: tokenBase }; },
      token: function(stream, state) {
        if (stream.eatSpace()) return null;
        return state.tokenize(stream, state);
      }
    };
  });

  CodeMirror.defineMIME("text/x-galaxian-basic", "galaxian-basic");
})();
