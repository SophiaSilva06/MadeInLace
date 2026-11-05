#!/usr/bin/env python3
"""
scan_diff.py - primeira peneira de seguranca sobre as linhas ALTERADAS de um PR.

Procura segredos (tokens, chaves, senhas hardcoded) e padroes perigosos comuns em
Python e JS/TS. E uma heuristica rapida: confirme cada achado lendo o contexto.
Ferramentas dedicadas (gitleaks, bandit, semgrep) continuam sendo recomendadas.

Uso:
  python scan_diff.py --base origin/main          # git diff base...HEAD (so linhas adicionadas)
  python scan_diff.py --staged                    # alteracoes em stage
  python scan_diff.py --diff-file mudancas.diff   # diff salvo ('-' le do stdin)
  python scan_diff.py --paths src/ app/           # varre arquivos inteiros
Opcoes: --json, --fail-on {critical,high,medium,low,never} (padrao: high)

Para ignorar uma linha (falso positivo justificado): adicione  secops:ignore  num comentario.
Segredos encontrados sao sempre mascarados na saida.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

SEV_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

SECRET_PATTERNS = [
    ("AWS Access Key ID", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "CRITICAL"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "CRITICAL"),
    ("GitHub fine-grained PAT", r"\bgithub_pat_[A-Za-z0-9_]{22,}\b", "CRITICAL"),
    ("GitLab PAT", r"\bglpat-[A-Za-z0-9_\-]{20,}\b", "CRITICAL"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b", "CRITICAL"),
    ("Stripe live key", r"\b[sr]k_live_[0-9a-zA-Z]{20,}\b", "CRITICAL"),
    ("Anthropic API key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b", "CRITICAL"),
    ("Chave privada (PEM/SSH)", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----", "CRITICAL"),
    ("Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "HIGH"),
    ("Chave estilo OpenAI", r"\bsk-[A-Za-z0-9]{32,}\b", "HIGH"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "HIGH"),
    ("URL com credenciais embutidas", r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^/\s:@'\"]+:[^/\s:@'\"]+@[^/\s'\"]+", "HIGH"),
    ("Segredo atribuido a variavel (hardcoded)",
     r"(?i)\b[\w.]*(?:password|passwd|pwd|secret|api[_-]?key|apikey|token|auth[_-]?token|access[_-]?key|private[_-]?key|client[_-]?secret)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']",
     "HIGH"),
]

# Valores claramente placeholder nao sao reportados como segredo hardcoded.
PLACEHOLDER = re.compile(
    r"(?i)(changeme|change_me|example|placeholder|your[_-]?|<[^>]+>|\$\{|\{\{|xxxx|\*\*\*\*|dummy|sample|todo|fake|test[_-]?(key|token|secret)|os\.environ|getenv|process\.env)"
)

# (nome, regex, severidade, extensoes alvo ou None para todas, dica de correcao)
RISKY = [
    ("eval/exec com dado dinamico", r"\b(?:eval|exec)\s*\(", "HIGH", {".py"}, "Evite eval/exec; use ast.literal_eval ou logica explicita."),
    ("Desserializacao insegura (pickle/marshal/dill)", r"\b(?:pickle|cPickle|marshal|dill|shelve)\.loads?\s*\(", "HIGH", {".py"}, "Nao desserialize dados externos; use JSON."),
    ("yaml.load sem SafeLoader", r"\byaml\.load\s*\((?![^)]*Safe(?:Loader|Dumper))", "HIGH", {".py", ".yml", ".yaml"}, "Use yaml.safe_load."),
    ("subprocess/os com shell", r"(?:shell\s*=\s*True|\bos\.(?:system|popen)\s*\()", "HIGH", {".py"}, "Use lista de argumentos sem shell e valide entradas."),
    ("SQL montado por string (f-string/format/%/+)",
     r"(?i)\.(?:execute|executemany|raw|extra)\s*\(\s*(?:f[\"']|[\"'][^\"']*[\"']\s*(?:%|\.format\s*\(|\+)|[^\"'\s)][^)]*\+)",
     "CRITICAL", {".py"}, "Use consultas parametrizadas (%s / :nome) ou o ORM."),
    ("text()/raw SQL com f-string", r"(?i)\b(?:text|RawSQL)\s*\(\s*f[\"']", "CRITICAL", {".py"}, "Use bind params: text('... :x'), {'x': valor}."),
    ("TLS sem verificacao", r"(?:verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|_create_unverified_context)", "HIGH", None, "Nao desative a verificacao de certificado."),
    ("DEBUG/reload ligado", r"(?:^|\s)DEBUG\s*=\s*True\b|debug\s*=\s*True|uvicorn[^\n]*--reload|reload\s*=\s*True", "HIGH", {".py"}, "DEBUG so em desenvolvimento, controlado por ambiente."),
    ("CORS totalmente aberto", r"(?:allow_origins\s*=\s*\[\s*[\"']\*[\"']|Access-Control-Allow-Origin[\"']?\s*[:,]\s*[\"']?\*)", "MEDIUM", None, "Defina origens explicitas; nunca '*' com credenciais."),
    ("|safe / Markup / autoescape off (Jinja2)", r"(?:\bMarkup\s*\(|\|\s*safe\b|autoescape\s+off|autoescape\s+false|autoescape\s*=\s*False)", "HIGH", {".py", ".html", ".jinja", ".j2", ".jinja2"}, "Escape por padrao; sanitize HTML rico (nh3/bleach)."),
    ("Template a partir de entrada (SSTI)", r"(?:\bTemplate\s*\(|\.from_string\s*\()\s*(?:request|f[\"']|[a-z_]+\s*\))", "HIGH", {".py"}, "Use templates estaticos e passe dados como contexto."),
    ("Hash fraco (md5/sha1)", r"\bhashlib\.(?:md5|sha1)\s*\(", "MEDIUM", {".py"}, "Para senhas: Argon2/bcrypt. Para integridade: SHA-256+."),
    ("random para valor sensivel", r"(?i)\brandom\.(?:random|randint|choice|choices|randrange)\s*\(.*(?:token|senha|password|secret|otp|code|key)|(?:token|password|secret|otp|key)\w*\s*=\s*.*\brandom\.", "HIGH", {".py"}, "Use o modulo secrets."),
    ("tarfile.extractall sem filtro", r"\.extractall\s*\((?![^)]*filter\s*=)", "MEDIUM", {".py"}, "Valide caminhos dos membros (zip/tar slip) ou use filter='data'."),
    ("assert usado em verificacao", r"^\s*assert\s+.*(?:permission|is_admin|is_authenticated|is_staff|user\.role)", "MEDIUM", {".py"}, "assert some com -O; use excecao explicita."),
    ("except generico silencioso", r"except\s*(?:Exception\s*)?:\s*(?:pass|continue)\b", "MEDIUM", {".py"}, "Trate/logue o erro e falhe fechado."),
    ("innerHTML/outerHTML/insertAdjacentHTML/document.write", r"(?:\.innerHTML\s*[+]?=|\.outerHTML\s*=|insertAdjacentHTML\s*\(|document\.write(?:ln)?\s*\()", "HIGH", {".js", ".mjs", ".ts", ".html"}, "Use textContent ou sanitize com DOMPurify."),
    ("eval/new Function (JS)", r"(?:\beval\s*\(|new\s+Function\s*\(|set(?:Timeout|Interval)\s*\(\s*[\"'`])", "HIGH", {".js", ".mjs", ".ts", ".html"}, "Nunca execute strings como codigo."),
    ("Token em localStorage/sessionStorage", r"(?i)(?:localStorage|sessionStorage)\.setItem\s*\(\s*[\"'`][^\"'`]*(?:token|jwt|auth|session|secret|password)", "MEDIUM", {".js", ".mjs", ".ts", ".html"}, "Prefira cookie HttpOnly/Secure/SameSite ou token apenas em memoria."),
    ("postMessage com origem '*'", r"postMessage\s*\([^)]*[\"']\*[\"']\s*\)", "MEDIUM", {".js", ".mjs", ".ts", ".html"}, "Informe targetOrigin exato e valide event.origin ao receber."),
    ("Dockerfile como root / tag latest", r"(?im)^\s*USER\s+root\b|^\s*FROM\s+\S+:latest\b|^\s*FROM\s+[^:\s@]+\s*$", "MEDIUM", {".dockerfile", ""}, "Use usuario nao-root e imagem base com tag/digest fixos."),
    ("curl | sh", r"(?:curl|wget)[^|\n]*\|\s*(?:sudo\s+)?(?:ba)?sh\b", "HIGH", None, "Baixe, verifique checksum/assinatura e so entao execute."),
    ("Workflow com permissao ampla / pull_request_target", r"(?:permissions\s*:\s*write-all|pull_request_target)", "MEDIUM", {".yml", ".yaml"}, "Permissoes minimas; cuidado com codigo de PR em contexto com segredos."),
    ("Interpolacao de contexto em run: (injecao no workflow)", r"run\s*:.*\$\{\{\s*github\.(?:event\.(?:pull_request\.(?:title|body|head\.ref)|issue\.(?:title|body)|comment\.body)|head_ref)", "HIGH", {".yml", ".yaml"}, "Passe via env: e use a variavel do shell entre aspas."),
]

SENSITIVE_FILES = re.compile(r"(?i)(?:^|/)(?:\.env(?:\.[\w.-]+)?|id_rsa|id_dsa|id_ecdsa|id_ed25519|.*\.(?:pem|p12|pfx|jks|keystore)|credentials(?:\.json)?|service[-_]?account.*\.json|\.npmrc|\.pypirc|.*\.sqlite3?|.*\.(?:dump|bak))$")
ENV_EXAMPLE = re.compile(r"(?i)\.(?:example|sample|template|dist)$")
SKIP_CONTENT = re.compile(r"(?i)(?:^|/)(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|uv\.lock|.*\.min\.(?:js|css)|.*\.map|.*\.svg|.*\.(?:png|jpe?g|gif|ico|pdf|woff2?|ttf|zip|gz))$")
MANIFESTS = re.compile(r"(?i)(?:^|/)(?:requirements[\w.-]*\.txt|pyproject\.toml|Pipfile|poetry\.lock|uv\.lock|package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Dockerfile[\w.-]*|docker-compose[\w.-]*\.ya?ml)$")


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return "****"
    return f"{v[:4]}****{v[-2:]} (len={len(v)})"


def entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in freq.values())


def ext_of(path: str) -> str:
    base = os.path.basename(path)
    if base.lower().startswith("dockerfile"):
        return ".dockerfile"
    return os.path.splitext(base)[1].lower()


def scan_line(path: str, lineno: int, line: str, findings: list):
    if "secops:ignore" in line:
        return
    if SKIP_CONTENT.search(path):
        return
    ext = ext_of(path)

    for name, rx, sev in SECRET_PATTERNS:
        m = re.search(rx, line)
        if not m:
            continue
        if name.startswith("Segredo atribuido") and PLACEHOLDER.search(m.group(0)):
            continue
        if name.startswith("URL com credenciais") and PLACEHOLDER.search(m.group(0)):
            continue
        findings.append({"file": path, "line": lineno, "severity": sev, "category": "Segredo",
                         "rule": name, "evidence": mask(m.group(0)),
                         "fix": "Revogue/rotacione a credencial, remova do codigo e leia de ambiente/secret manager."})

    # entropia alta em atribuicao com palavra-chave sensivel
    for m in re.finditer(r"(?i)(?:key|token|secret|passw\w*|credential)\w*[\"']?\s*[:=]\s*[\"']([A-Za-z0-9+/=_\-]{24,})[\"']", line):
        val = m.group(1)
        if entropy(val) >= 4.0 and not PLACEHOLDER.search(val) and not any(
                f["file"] == path and f["line"] == lineno and f["category"] == "Segredo" for f in findings):
            findings.append({"file": path, "line": lineno, "severity": "MEDIUM", "category": "Segredo",
                             "rule": "String de alta entropia em atribuicao sensivel", "evidence": mask(val),
                             "fix": "Confirme se e credencial real; se for, rotacione e mova para ambiente."})

    for name, rx, sev, exts, fix in RISKY:
        if exts is not None and ext not in exts:
            continue
        if re.search(rx, line):
            findings.append({"file": path, "line": lineno, "severity": sev, "category": "Padrao perigoso",
                             "rule": name, "evidence": line.strip()[:140], "fix": fix})


def check_file_name(path: str, findings: list):
    if SENSITIVE_FILES.search(path) and not ENV_EXAMPLE.search(path):
        findings.append({"file": path, "line": 0, "severity": "HIGH", "category": "Segredo",
                         "rule": "Arquivo tipicamente sensivel no PR", "evidence": os.path.basename(path),
                         "fix": "Nao versione este arquivo; adicione ao .gitignore e rotacione se tiver credenciais reais."})


def parse_diff(text: str):
    """Gera (arquivo, numero_da_linha, conteudo) so das linhas ADICIONADAS."""
    path, new_line, files = None, 0, []
    for raw in text.splitlines():
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            path = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
            if path:
                files.append(path)
            continue
        if raw.startswith("--- ") or raw.startswith("diff --git") or raw.startswith("index "):
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            new_line = int(m.group(1))
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            yield path, new_line, raw[1:]
            new_line += 1
        elif raw.startswith("-"):
            continue
        else:
            new_line += 1
    yield ("__files__", 0, files)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Erro ao executar {' '.join(cmd)}: {r.stderr.strip()}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description="Varredura de seguranca nas linhas alteradas de um PR/diff.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--base", help="ref base; usa git diff BASE...HEAD")
    g.add_argument("--staged", action="store_true", help="usa git diff --cached")
    g.add_argument("--diff-file", help="arquivo com diff unificado ('-' = stdin)")
    g.add_argument("--paths", nargs="+", help="arquivos/diretorios a varrer por inteiro")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    ap.add_argument("--fail-on", default="high", choices=["critical", "high", "medium", "low", "never"])
    a = ap.parse_args()

    findings, changed_files = [], []
    if a.paths:
        for p in a.paths:
            walk = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, ds, fs in os.walk(p)
                                                   if not any(x in d.split(os.sep) for x in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"))
                                                   for f in fs]
            for fp in walk:
                changed_files.append(fp)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh, 1):
                            scan_line(fp, i, line.rstrip("\n"), findings)
                except OSError:
                    pass
    else:
        if a.base:
            text = run(["git", "diff", "-U0", f"{a.base}...HEAD"])
        elif a.staged:
            text = run(["git", "diff", "-U0", "--cached"])
        elif a.diff_file == "-":
            text = sys.stdin.read()
        else:
            with open(a.diff_file, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        for path, ln, content in parse_diff(text):
            if path == "__files__":
                changed_files = content
                continue
            scan_line(path, ln, content, findings)

    for f in changed_files:
        check_file_name(f, findings)
    manifests = [f for f in changed_files if MANIFESTS.search(f)]

    findings.sort(key=lambda x: (-SEV_ORDER[x["severity"]], x["file"], x["line"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV_ORDER}

    if a.json:
        print(json.dumps({"arquivos_analisados": len(changed_files), "contagem": counts,
                          "manifestos_alterados": manifests, "achados": findings}, ensure_ascii=False, indent=2))
    else:
        print(f"Arquivos analisados: {len(changed_files)} | CRITICAL={counts['CRITICAL']} HIGH={counts['HIGH']} "
              f"MEDIUM={counts['MEDIUM']} LOW={counts['LOW']}")
        for f in findings:
            loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            print(f"\n[{f['severity']}] {f['category']} - {f['rule']}\n  {loc}\n  evidencia: {f['evidence']}\n  correcao: {f['fix']}")
        if manifests:
            print("\nManifestos/lockfiles/Docker alterados (rodar auditoria de dependencias: scripts/audit_deps.sh):")
            for m in manifests:
                print(f"  - {m}")
        if not findings:
            print("\nNenhum padrao suspeito encontrado pelas heuristicas. Isso NAO substitui a revisao manual linha a linha.")

    if a.fail_on != "never":
        limit = SEV_ORDER[a.fail_on.upper()]
        if any(SEV_ORDER[f["severity"]] >= limit for f in findings):
            sys.exit(1)


if __name__ == "__main__":
    main()
