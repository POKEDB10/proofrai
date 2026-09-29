import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ALLOWED_BACKEND_PACKAGES = {
    "fastapi",
    "uvicorn",
    "pydantic",
    "pyyaml",
    "sqlalchemy",
    "httpx",
    "google-genai",
    "google_genai",
    "pytest",
    "ruff",
}

ALLOWED_FRONTEND_PACKAGES = {
    "react",
    "react-dom",
    "react-router-dom",
    "vite",
    "typescript",
    "@vitejs/plugin-react",
    "@fontsource/ibm-plex-sans",
    "@fontsource/ibm-plex-mono",
}

BANNED_PACKAGES = {
    "tailwindcss",
    "shadcn/ui",
    "@shadcn/ui",
    "radix-ui",
    "@radix-ui",
    "mui",
    "@mui/material",
    "@mui",
    "chakra",
    "@chakra-ui/react",
    "antd",
    "mantine",
    "@mantine/core",
    "framer-motion",
    "lucide-react",
    "font-awesome",
    "@fortawesome/fontawesome-free",
    "heroicons",
    "@heroicons/react",
    "react-icons",
    "redux",
    "@reduxjs/toolkit",
    "zustand",
    "axios",
    "pandas",
}

BANNED_CSS_WORDS = [
    "gradient",
    "box-shadow",
    "text-shadow",
    "backdrop-filter",
    "blur(",
]

BANNED_FONTS = [
    "Inter",
    "Roboto",
    "system-ui",
    "-apple-system",
    "Poppins",
    "DM Sans",
    "Manrope",
    "Space Grotesk",
]

BANNED_WORDS = [
    "seamless",
    "powerful",
    "unlock",
    "leverage",
    "robust",
    "cutting-edge",
    "revolutionize",
    "effortless",
    "delve",
    "elevate",
    "game-changing",
    "next-generation",
    "empower",
    "streamline",
    "ai-powered",
    "state-of-the-art",
]

BANNED_WORDS_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(
        [
            w.replace("-", r"[- ]")
            for w in BANNED_WORDS
        ]
    )
    + r")\b",
    re.IGNORECASE,
)

RIGHT_ARROWS = ["\u2192", "\u21d2", "\u2794", "\u279c", "\u279d"]


@dataclass
class Violation:
    file: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.message}"


def is_emoji_char(char: str) -> bool:
    code = ord(char)
    if (
        0x1F600 <= code <= 0x1F64F
        or 0x1F300 <= code <= 0x1F5FF
        or 0x1F680 <= code <= 0x1F6FF
        or 0x1F700 <= code <= 0x1F77F
        or 0x1F780 <= code <= 0x1F7FF
        or 0x1F800 <= code <= 0x1F8FF
        or 0x1F900 <= code <= 0x1F9FF
        or 0x1FA00 <= code <= 0x1FA6F
        or 0x1FA70 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x26FF
        or 0x2700 <= code <= 0x27BF
        or code == 0xFE0F
    ):
        return True
    category = unicodedata.category(char)
    name = unicodedata.name(char, "")
    return category == "So" and ("EMOJI" in name or "FACE" in name)


def check_frontend_css(content: str, filename: str) -> list[Violation]:
    violations: list[Violation] = []
    lines = content.splitlines()
    is_tokens = Path(filename).name == "tokens.css"

    for idx, line in enumerate(lines, start=1):
        line_lower = line.lower()

        for word in BANNED_CSS_WORDS:
            if word in line_lower:
                violations.append(
                    Violation(filename, idx, f"banned CSS feature '{word}'")
                )

        if not is_tokens:
            if re.search(r"#[0-9a-fA-F]{3,8}\b", line):
                violations.append(
                    Violation(filename, idx, "color literal hex outside tokens.css")
                )
            if re.search(r"\b(?:rgb|rgba|hsl|hsla)\s*\(", line_lower):
                violations.append(
                    Violation(filename, idx, "color literal function outside tokens.css")
                )
            for font in BANNED_FONTS:
                if re.search(rf"\b{re.escape(font.lower())}\b", line_lower):
                    violations.append(
                        Violation(
                            filename,
                            idx,
                            f"banned font '{font}' outside tokens.css",
                        )
                    )

        if re.search(r"text-transform\s*:\s*uppercase", line_lower):
            violations.append(
                Violation(filename, idx, "text-transform uppercase is not allowed")
            )

        match_ls = re.search(r"letter-spacing\s*:\s*([^;]+)", line_lower)
        if match_ls:
            raw_val = match_ls.group(1).strip()
            val_match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*(em|px|rem)?$", raw_val)
            if val_match:
                num = float(val_match.group(1))
                unit = val_match.group(2) or "px"
                if unit == "em" and num > 0.02 or unit == "px" and num > 0.32 or unit == "rem" and num > 0.02:
                    violations.append(
                        Violation(filename, idx, f"letter-spacing {raw_val} exceeds 0.02em")
                    )

        border_match = re.search(
            r"(?:border-left|border-inline-start)(?:-width)?\s*:\s*([^;]+)",
            line_lower,
        )
        if border_match:
            raw_val = border_match.group(1).strip()
            px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", raw_val)
            if px_match:
                width = float(px_match.group(1))
                if width >= 2.0:
                    violations.append(
                        Violation(
                            filename,
                            idx,
                            f"border-left or border-inline-start width {raw_val} >= 2px",
                        )
                    )
            elif any(k in raw_val for k in ["medium", "thick"]):
                violations.append(
                    Violation(
                        filename,
                        idx,
                        f"border-left width '{raw_val}' exceeds 2px",
                    )
                )

        radius_match = re.search(r"border-radius\s*:\s*([^;]+)", line_lower)
        if radius_match:
            raw_val = radius_match.group(1).strip()
            tokens = raw_val.split()
            for token in tokens:
                if token in ("0", "0px"):
                    continue
                if re.match(r"^var\(--radius-[a-zA-Z0-9_-]+\)$", token):
                    continue
                violations.append(
                    Violation(
                        filename,
                        idx,
                        f"border-radius '{token}' is not 0 or a var(--radius-...) token",
                    )
                )
                break

        if re.search(r"transition(?:-property)?\s*:\s*all\b", line_lower):
            violations.append(
                Violation(filename, idx, "transition: all is not allowed")
            )

        anim_match = re.search(r"animation(?:-name)?\s*:\s*([^;]+)", line_lower)
        if anim_match:
            raw_val = anim_match.group(1).strip()
            standard_keywords = {
                "none",
                "ease",
                "linear",
                "ease-in",
                "ease-out",
                "ease-in-out",
                "forwards",
                "backwards",
                "both",
                "infinite",
                "normal",
                "reverse",
                "alternate",
                "alternate-reverse",
                "running",
                "paused",
                "cell-in",
            }
            tokens = raw_val.split()
            for token in tokens:
                if re.match(r"^\d+(?:\.\d+)?(?:ms|s)$", token):
                    continue
                if re.match(r"^\d+$", token):
                    continue
                if token not in standard_keywords:
                    violations.append(
                        Violation(
                            filename,
                            idx,
                            f"animation name '{token}' not allowed (only cell-in)",
                        )
                    )

    return violations


def check_text_rules(content: str, filename: str) -> list[Violation]:
    violations: list[Violation] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        for char in line:
            if is_emoji_char(char):
                violations.append(
                    Violation(filename, idx, f"emoji character '{char}' is forbidden")
                )
                break

        if "\u2014" in line:
            violations.append(
                Violation(filename, idx, "em dash character is forbidden")
            )

        for arrow in RIGHT_ARROWS:
            if arrow in line:
                violations.append(
                    Violation(
                        filename,
                        idx,
                        f"right arrow character '{arrow}' is forbidden",
                    )
                )
                break

        if re.search(r"\w\s*[\u00b7\u2022]\s*\w", line):
            violations.append(
                Violation(
                    filename,
                    idx,
                    "middle dot separator between words is forbidden",
                )
            )

        for match_word in BANNED_WORDS_PATTERN.finditer(line):
            word = match_word.group(0)
            violations.append(
                Violation(filename, idx, f"banned word '{word}' found")
            )

    return violations


def check_package_json(content: str, filename: str) -> list[Violation]:
    violations: list[Violation] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [Violation(filename, 1, f"invalid json: {exc}")]

    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    all_packages = list(deps.keys()) + list(dev_deps.keys())

    lines = content.splitlines()

    def find_line(pkg_name: str) -> int:
        for idx, line in enumerate(lines, start=1):
            if f'"{pkg_name}"' in line:
                return idx
        return 1

    for pkg in all_packages:
        line_num = find_line(pkg)
        if pkg in BANNED_PACKAGES or any(
            pkg.startswith(f"{b}/") for b in BANNED_PACKAGES
        ):
            violations.append(
                Violation(
                    filename,
                    line_num,
                    f"package '{pkg}' is explicitly banned by rule 17",
                )
            )
        elif pkg not in ALLOWED_FRONTEND_PACKAGES:
            violations.append(
                Violation(
                    filename,
                    line_num,
                    f"package '{pkg}' is not in allowed frontend packages (rule 15)",
                )
            )

    return violations


def check_requirements_txt(content: str, filename: str) -> list[Violation]:
    violations: list[Violation] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        pkg = re.split(r"[><=~;!]", stripped)[0].strip().lower()
        if not pkg:
            continue

        if pkg in BANNED_PACKAGES:
            violations.append(
                Violation(
                    filename,
                    idx,
                    f"package '{pkg}' is explicitly banned by rule 17",
                )
            )
        elif pkg not in ALLOWED_BACKEND_PACKAGES:
            violations.append(
                Violation(
                    filename,
                    idx,
                    f"package '{pkg}' is not in allowed backend packages (rule 14)",
                )
            )

    return violations


def check_print_statements(content: str, filename: str) -> list[Violation]:
    norm = Path(filename).as_posix()
    if norm.endswith(("core/suite/cli.py", "core/target/demo.py")):
        return []

    violations: list[Violation] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\bprint\s*\(", line):
            violations.append(
                Violation(filename, idx, "print() is not allowed here")
            )

    return violations


def scan_repository(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []

    frontend_src = repo_root / "frontend" / "src"
    if frontend_src.is_dir():
        for file_path in frontend_src.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            rel_path = file_path.relative_to(repo_root).as_posix()

            if file_path.suffix in [".css", ".ts", ".tsx", ".js", ".jsx"]:
                violations.extend(check_frontend_css(content, rel_path))

            violations.extend(check_text_rules(content, rel_path))

    for text_doc in [repo_root / "README.md"]:
        if text_doc.is_file():
            content = text_doc.read_text(encoding="utf-8")
            rel_path = text_doc.relative_to(repo_root).as_posix()
            violations.extend(check_text_rules(content, rel_path))

    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for file_path in docs_dir.rglob("*.md"):
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8")
                rel_path = file_path.relative_to(repo_root).as_posix()
                violations.extend(check_text_rules(content, rel_path))

    pkg_json = repo_root / "frontend" / "package.json"
    if pkg_json.is_file():
        content = pkg_json.read_text(encoding="utf-8")
        rel_path = pkg_json.relative_to(repo_root).as_posix()
        violations.extend(check_package_json(content, rel_path))

    req_txt = repo_root / "backend" / "requirements.txt"
    if req_txt.is_file():
        content = req_txt.read_text(encoding="utf-8")
        rel_path = req_txt.relative_to(repo_root).as_posix()
        violations.extend(check_requirements_txt(content, rel_path))

    for backend_dir in [repo_root / "backend" / "core", repo_root / "backend" / "app"]:
        if backend_dir.is_dir():
            for file_path in backend_dir.rglob("*.py"):
                if file_path.is_file():
                    content = file_path.read_text(encoding="utf-8")
                    rel_path = file_path.relative_to(repo_root).as_posix()
                    violations.extend(check_print_statements(content, rel_path))

    return violations


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    violations = scan_repository(repo_root)

    if violations:
        for violation in violations:
            sys.stderr.write(f"{violation}\n")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
