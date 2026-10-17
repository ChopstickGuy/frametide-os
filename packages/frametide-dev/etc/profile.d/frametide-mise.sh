# Mit mise installierte Sprachen (Python, Node.js, Go, Rust …) überall verfügbar machen –
# auch in grafischen Programmen wie VS Code (Shims statt Shell-Hook).
if [ -d "$HOME/.local/share/mise/shims" ] || command -v mise >/dev/null 2>&1; then
    case ":$PATH:" in
        *":$HOME/.local/share/mise/shims:"*) ;;
        *) PATH="$HOME/.local/share/mise/shims:$PATH"; export PATH ;;
    esac
fi
