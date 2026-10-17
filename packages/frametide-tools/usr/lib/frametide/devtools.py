"""Logik für die Frametide Entwicklerzentrale: Git/SSH/GitHub, Sprachen (mise),
lokale Datenbanken (Podman), offene Ports und Projektvorlagen."""
import json
import os
import re
import shutil
import subprocess

from frametide_i18n import _

HOME = os.path.expanduser("~")
SSH_KEY = os.path.join(HOME, ".ssh", "id_ed25519")


def run(argv, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 127, str(e)


def have(tool):
    return shutil.which(tool) is not None


# ------------------------------------------------------------------- Git & SSH

def git_identity():
    return run(["git", "config", "--global", "user.name"])[1], run(["git", "config", "--global", "user.email"])[1]


def set_git_identity(name, email):
    for key, value in (("user.name", name), ("user.email", email), ("init.defaultBranch", "main"),
                       ("pull.rebase", "false"), ("push.autoSetupRemote", "true")):
        run(["git", "config", "--global", key, value])


def ssh_public_key():
    path = SSH_KEY + ".pub"
    return open(path).read().strip() if os.path.exists(path) else None


def create_ssh_key(comment):
    os.makedirs(os.path.dirname(SSH_KEY), mode=0o700, exist_ok=True)
    return run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", comment or "frametide", "-f", SSH_KEY])[0] == 0


def github_status():
    """GitHub-Benutzername oder None."""
    if not have("gh"):
        return None
    code, out = run(["gh", "auth", "status", "--hostname", "github.com"])
    m = re.search(r"account (\S+)", out) or re.search(r"as (\S+)", out)
    return m.group(1) if code == 0 and m else None


# ---------------------------------------------------------------- Sprachen (mise)

LANGUAGES = [
    # mise-Name, Anzeigename, Befehl zur Versionsprüfung
    ("python", "Python", "python"),
    ("node", "Node.js", "node"),
    ("go", "Go", "go"),
    ("rust", "Rust", "cargo"),
    ("java", "Java (OpenJDK)", "java"),
    ("bun", "Bun", "bun"),
    ("deno", "Deno", "deno"),
    ("ruby", "Ruby", "ruby"),
    ("zig", "Zig", "zig"),
]


def mise_installed_tools():
    """{Werkzeug: Version} der global aktiven mise-Werkzeuge."""
    if not have("mise"):
        return {}
    code, out = run(["mise", "ls", "--global", "--json"], timeout=20)
    if code != 0:
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    result = {}
    for tool, versions in data.items():
        active = [v.get("version") for v in versions if v.get("active") or v.get("installed")]
        if active:
            result[tool] = active[-1]
    return result


def mise_install_argv(tool):
    return ["mise", "use", "--global", "--yes", f"{tool}@latest"]


# ------------------------------------------------------------- Lokale Dienste

SERVICES = [
    # id, Name, Image, Port, Umgebungsvariablen, Datenpfad im Container, Verbindungs-URL
    ("postgres", "PostgreSQL 17", "docker.io/library/postgres:17", 5432,
     {"POSTGRES_PASSWORD": "frametide", "POSTGRES_USER": "dev", "POSTGRES_DB": "dev"},
     "/var/lib/postgresql/data", "postgresql://dev:frametide@localhost:5432/dev"),
    ("mysql", "MySQL 8.4", "docker.io/library/mysql:8.4", 3306,
     {"MYSQL_ROOT_PASSWORD": "frametide", "MYSQL_DATABASE": "dev", "MYSQL_USER": "dev", "MYSQL_PASSWORD": "frametide"},
     "/var/lib/mysql", "mysql://dev:frametide@localhost:3306/dev"),
    ("mariadb", "MariaDB 11", "docker.io/library/mariadb:11", 3307,
     {"MARIADB_ROOT_PASSWORD": "frametide", "MARIADB_DATABASE": "dev", "MARIADB_USER": "dev",
      "MARIADB_PASSWORD": "frametide"},
     "/var/lib/mysql", "mysql://dev:frametide@localhost:3307/dev"),
    ("redis", "Redis 7", "docker.io/library/redis:7", 6379, {}, "/data", "redis://localhost:6379"),
    ("mongo", "MongoDB 8", "docker.io/library/mongo:8", 27017,
     {"MONGO_INITDB_ROOT_USERNAME": "dev", "MONGO_INITDB_ROOT_PASSWORD": "frametide"},
     "/data/db", "mongodb://dev:frametide@localhost:27017"),
    ("adminer", "Adminer (Datenbank-Weboberfläche)", "docker.io/library/adminer:latest", 8089, {}, None,
     "http://localhost:8089"),
]


def container_name(service_id):
    return f"ft-db-{service_id}"


def service_states():
    """{service_id: 'running' | 'stopped'} für angelegte Dienst-Container."""
    if not have("podman"):
        return {}
    code, out = run(["podman", "ps", "-a", "--format", "{{.Names}} {{.State}}"])
    states = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("ft-db-"):
            states[parts[0][6:]] = "running" if parts[1].lower() in ("running", "up") else "stopped"
    return states


def service_start_argv(service):
    sid, _name, image, port, env, data, _url = service
    name = container_name(sid)
    if sid in service_states():
        return ["podman", "start", name]
    inner = 8080 if sid == "adminer" else port if sid != "mariadb" else 3306
    argv = ["podman", "run", "-d", "--name", name, "-p", f"127.0.0.1:{port}:{inner}"]
    for key, value in env.items():
        argv += ["-e", f"{key}={value}"]
    if data:
        argv += ["-v", f"{name}:{data}"]
    return argv + [image]


def service_stop_argv(service):
    return ["podman", "stop", container_name(service[0])]


# ------------------------------------------------------------------- Ports

def listening_ports():
    """[(Port, Programm, PID, Adresse)] – eigene Prozesse, die auf TCP-Ports lauschen."""
    code, out = run(["ss", "-ltnpH"])
    result, seen = [], set()
    for line in out.splitlines():
        cols = line.split()
        if len(cols) < 5:
            continue
        addr = cols[3]
        port = int(addr.rsplit(":", 1)[-1]) if addr.rsplit(":", 1)[-1].isdigit() else None
        m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        if port and m and port not in seen:
            seen.add(port)
            result.append((port, m.group(1), int(m.group(2)), addr.rsplit(":", 1)[0].strip("[]")))
    return sorted(result)


# ------------------------------------------------------------- Projektvorlagen

GITIGNORE_COMMON = ".DS_Store\n.idea/\n*.log\n.env\n.env.local\n"
EDITORCONFIG = ("root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n"
                "indent_style = space\nindent_size = 4\n\n[*.{js,ts,tsx,json,yml,yaml,css,html}]\nindent_size = 2\n")

TEMPLATES = {
    "python": {
        "name": "Python (FastAPI)", "mise": {"python": "latest"},
        "devcontainer": "mcr.microsoft.com/devcontainers/python:3",
        "extensions": ["ms-python.python", "charliermarsh.ruff"],
        "gitignore": "__pycache__/\n*.pyc\n.venv/\n.pytest_cache/\n",
        "run": "python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt\n"
               "uvicorn app.main:app --reload",
        "files": {
            "requirements.txt": "fastapi\nuvicorn[standard]\n",
            "app/__init__.py": "",
            "app/main.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="{name}")\n\n\n'
                           '@app.get("/")\ndef hello():\n    return {{"message": "Hallo von {name}!"}}\n',
        },
    },
    "node": {
        "name": "Node.js (TypeScript)", "mise": {"node": "lts"},
        "devcontainer": "mcr.microsoft.com/devcontainers/typescript-node:22",
        "extensions": ["dbaeumer.vscode-eslint", "esbenp.prettier-vscode"],
        "gitignore": "node_modules/\ndist/\n",
        "run": "npm install\nnpm run dev",
        "files": {
            "package.json": '{{\n  "name": "{slug}",\n  "version": "0.1.0",\n  "type": "module",\n'
                            '  "scripts": {{ "dev": "tsx watch src/index.ts", "build": "tsc" }},\n'
                            '  "devDependencies": {{ "tsx": "^4", "typescript": "^5", "@types/node": "^22" }}\n}}\n',
            "tsconfig.json": '{\n  "compilerOptions": { "target": "ES2022", "module": "NodeNext", "strict": true,\n'
                             '    "outDir": "dist" },\n  "include": ["src"]\n}\n',
            "src/index.ts": 'console.log("Hallo von {name}!");\n',
        },
    },
    "react": {
        "name": "React (Vite + TypeScript)", "mise": {"node": "lts"},
        "devcontainer": "mcr.microsoft.com/devcontainers/typescript-node:22",
        "extensions": ["dbaeumer.vscode-eslint", "esbenp.prettier-vscode"],
        "gitignore": "node_modules/\ndist/\n",
        "run": "npm install\nnpm run dev",
        "files": {
            "package.json": '{{\n  "name": "{slug}",\n  "version": "0.1.0",\n  "type": "module",\n'
                            '  "scripts": {{ "dev": "vite", "build": "tsc && vite build", "preview": "vite preview" }},\n'
                            '  "dependencies": {{ "react": "^19", "react-dom": "^19" }},\n'
                            '  "devDependencies": {{ "@vitejs/plugin-react": "^5", "typescript": "^5", "vite": "^7",\n'
                            '    "@types/react": "^19", "@types/react-dom": "^19" }}\n}}\n',
            "vite.config.ts": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\n'
                              'export default defineConfig({ plugins: [react()] });\n',
            "tsconfig.json": '{\n  "compilerOptions": { "target": "ES2022", "module": "ESNext", "jsx": "react-jsx",\n'
                             '    "moduleResolution": "bundler", "strict": true, "noEmit": true },\n'
                             '  "include": ["src"]\n}\n',
            "index.html": '<!doctype html>\n<html lang="de">\n  <head><meta charset="UTF-8" /><title>{name}</title></head>\n'
                          '  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>\n'
                          '</html>\n',
            "src/main.tsx": 'import { createRoot } from "react-dom/client";\n\n'
                            'createRoot(document.getElementById("root")!).render(<h1>Hallo von {name}!</h1>);\n',
        },
    },
    "rust": {
        "name": "Rust", "mise": {"rust": "stable"},
        "devcontainer": "mcr.microsoft.com/devcontainers/rust:1",
        "extensions": ["rust-lang.rust-analyzer"],
        "gitignore": "target/\n",
        "run": "cargo run",
        "files": {
            "Cargo.toml": '[package]\nname = "{slug}"\nversion = "0.1.0"\nedition = "2024"\n\n[dependencies]\n',
            "src/main.rs": 'fn main() {{\n    println!("Hallo von {name}!");\n}}\n',
        },
    },
    "go": {
        "name": "Go", "mise": {"go": "latest"},
        "devcontainer": "mcr.microsoft.com/devcontainers/go:1",
        "extensions": ["golang.go"],
        "gitignore": "/bin/\n",
        "run": "go run .",
        "files": {
            "go.mod": "module {slug}\n\ngo 1.24\n",
            "main.go": 'package main\n\nimport "fmt"\n\nfunc main() {{\n\tfmt.Println("Hallo von {name}!")\n}}\n',
        },
    },
    "cpp": {
        "name": "C++ (CMake)", "mise": {},
        "devcontainer": "mcr.microsoft.com/devcontainers/cpp:1",
        "extensions": ["ms-vscode.cpptools", "ms-vscode.cmake-tools"],
        "gitignore": "build/\n",
        "run": "cmake -B build && cmake --build build && ./build/{slug}",
        "files": {
            "CMakeLists.txt": "cmake_minimum_required(VERSION 3.25)\nproject({slug} CXX)\n"
                              "set(CMAKE_CXX_STANDARD 23)\nadd_executable({slug} src/main.cpp)\n",
            "src/main.cpp": '#include <print>\n\nint main() {{\n    std::println("Hallo von {name}!");\n}}\n',
        },
    },
    "web": {
        "name": "Website (HTML/CSS/JS)", "mise": {},
        "devcontainer": "mcr.microsoft.com/devcontainers/base:ubuntu",
        "extensions": ["ritwickdey.LiveServer"],
        "gitignore": "",
        "run": "python3 -m http.server 8000   # dann http://localhost:8000 öffnen",
        "files": {
            "index.html": '<!doctype html>\n<html lang="de">\n<head>\n  <meta charset="utf-8">\n'
                          '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
                          '  <title>{name}</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n'
                          '<body>\n  <h1>{name}</h1>\n  <script src="main.js"></script>\n</body>\n</html>\n',
            "style.css": "body {{ font-family: system-ui, sans-serif; margin: 3rem; }}\n",
            "main.js": 'console.log("Hallo von {name}!");\n',
        },
    },
    "godot": {
        "name": "Godot-Spiel", "mise": {},
        "devcontainer": None,
        "extensions": ["geequlim.godot-tools"],
        "gitignore": ".godot/\n*.import\nexport/\n",
        "run": "Projekt in Godot öffnen (Godot gibt es im App Store).",
        "files": {
            "project.godot": '; Godot 4 Projekt\nconfig_version=5\n\n[application]\nconfig/name="{name}"\n'
                             'run/main_scene="res://main.tscn"\n',
            "main.tscn": '[gd_scene format=3]\n\n[node name="Main" type="Node2D"]\n',
        },
    },
}


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "projekt"


def create_project(base_dir, name, template_id, git=True, devcontainer=True):
    """Legt das Projekt an und gibt den Pfad zurück."""
    t = TEMPLATES[template_id]
    slug = slugify(name)
    path = os.path.join(base_dir, slug)
    if os.path.exists(path) and os.listdir(path):
        raise FileExistsError(_("Der Ordner {path} existiert bereits.").format(path=path))
    os.makedirs(path, exist_ok=True)

    def write(rel, content):
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    def fill(text):  # Platzhalter {name}/{slug}; doppelte Klammern stehen für einfache
        return (text.replace("{name}", name).replace("{slug}", slug)
                .replace("{{", "{").replace("}}", "}"))

    for rel, content in t["files"].items():
        write(rel, fill(content))
    write(".gitignore", t["gitignore"] + GITIGNORE_COMMON)
    write(".editorconfig", EDITORCONFIG)
    write(".vscode/extensions.json", json.dumps({"recommendations": t["extensions"]}, indent=2) + "\n")
    if t["mise"]:
        write("mise.toml", "[tools]\n" + "".join(f'{k} = "{v}"\n' for k, v in t["mise"].items()))
    if devcontainer and t["devcontainer"]:
        write(".devcontainer/devcontainer.json", json.dumps(
            {"name": name, "image": t["devcontainer"],
             "customizations": {"vscode": {"extensions": t["extensions"]}}}, indent=2) + "\n")
    run_cmd = fill(t["run"])
    write("README.md", f"# {name}\n\n" + _("Erstellt mit Frametide OS ({template}).").format(template=t["name"])
          + "\n\n## " + _("Starten") + "\n\n```bash\n" + run_cmd + "\n```\n")
    if git and have("git"):
        run(["git", "init", "-q", path])
        if all(git_identity()):
            run(["git", "-C", path, "add", "-A"])
            run(["git", "-C", path, "commit", "-q", "-m", _("Projekt angelegt")])
    return path
