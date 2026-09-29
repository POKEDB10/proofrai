from scripts.style_check import (
    check_frontend_css,
    check_package_json,
    check_print_statements,
    check_requirements_txt,
    check_text_rules,
)


def test_banned_css_words() -> None:
    bad_css = """
    .card {
      background: linear-gradient(to right, red, blue);
      box-shadow: 0 2px 4px black;
      text-shadow: 1px 1px black;
      backdrop-filter: blur(4px);
    }
    """
    violations = check_frontend_css(bad_css, "frontend/src/styles/bad.css")
    messages = [v.message for v in violations]
    assert any("gradient" in m for m in messages)
    assert any("box-shadow" in m for m in messages)
    assert any("text-shadow" in m for m in messages)
    assert any("backdrop-filter" in m for m in messages)
    assert any("blur(" in m for m in messages)


def test_color_literals() -> None:
    bad_css = """
    .btn {
      color: #123456;
      background: rgb(255, 0, 0);
      border-color: hsl(120, 50%, 50%);
    }
    """
    violations = check_frontend_css(bad_css, "frontend/src/styles/test.css")
    messages = [v.message for v in violations]
    assert any("hex" in m for m in messages)
    assert any("function" in m for m in messages)

    tokens_css = """
    :root {
      --ink: #1E2530;
      --pass: #1B6E4F;
    }
    """
    assert check_frontend_css(tokens_css, "frontend/src/styles/tokens.css") == []


def test_banned_fonts() -> None:
    bad_css = "body { font-family: Inter, Roboto, sans-serif; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert len(violations) >= 2


def test_text_transform_uppercase() -> None:
    bad_css = "h1 { text-transform: uppercase; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("text-transform uppercase" in v.message for v in violations)


def test_letter_spacing() -> None:
    bad_css = "p { letter-spacing: 0.05em; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("letter-spacing" in v.message for v in violations)

    clean_css = "p { letter-spacing: 0.02em; }"
    assert check_frontend_css(clean_css, "frontend/src/styles/main.css") == []


def test_border_left_width() -> None:
    bad_css = ".callout { border-left: 3px solid red; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("border-left" in v.message for v in violations)

    clean_css = ".item { border-left: 1px solid var(--rule); }"
    assert check_frontend_css(clean_css, "frontend/src/styles/main.css") == []


def test_border_radius() -> None:
    bad_css = ".box { border-radius: 4px; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("border-radius" in v.message for v in violations)

    clean_css = ".box { border-radius: var(--radius-control); }"
    assert check_frontend_css(clean_css, "frontend/src/styles/main.css") == []

    zero_css = ".box { border-radius: 0; }"
    assert check_frontend_css(zero_css, "frontend/src/styles/main.css") == []


def test_transition_all() -> None:
    bad_css = ".card { transition: all 0.2s ease; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("transition: all" in v.message for v in violations)


def test_animation_names() -> None:
    bad_css = ".item { animation: spin 1s infinite; }"
    violations = check_frontend_css(bad_css, "frontend/src/styles/main.css")
    assert any("animation name 'spin'" in v.message for v in violations)

    clean_css = ".cell { animation: cell-in 120ms ease; }"
    assert check_frontend_css(clean_css, "frontend/src/styles/main.css") == []


def test_forbidden_text_characters() -> None:
    emoji_text = "Here is a rocket: \U0001F680"
    assert any("emoji" in v.message for v in check_text_rules(emoji_text, "README.md"))

    em_dash_text = "This is a sentence — with an em dash."
    assert any("em dash" in v.message for v in check_text_rules(em_dash_text, "README.md"))

    arrow_text = "Step A \u2192 Step B"
    assert any("arrow" in v.message for v in check_text_rules(arrow_text, "README.md"))

    middle_dot_text = "Word · separator"
    assert any("middle dot" in v.message for v in check_text_rules(middle_dot_text, "README.md"))


def test_banned_marketing_words() -> None:
    bad_text = "This is a seamless and powerful workflow."
    violations = check_text_rules(bad_text, "docs/decisions.md")
    assert len(violations) >= 2


def test_frontend_packages() -> None:
    bad_pkg = '{"dependencies": {"axios": "1.0.0"}}'
    violations = check_package_json(bad_pkg, "frontend/package.json")
    assert any("banned by rule 17" in v.message for v in violations)

    unallowed_pkg = '{"dependencies": {"lodash": "4.17.21"}}'
    violations = check_package_json(unallowed_pkg, "frontend/package.json")
    assert any("not in allowed frontend packages" in v.message for v in violations)

    clean_pkg = '{"dependencies": {"react": "19.0.0", "react-dom": "19.0.0"}}'
    assert check_package_json(clean_pkg, "frontend/package.json") == []


def test_backend_packages() -> None:
    bad_req = "pandas>=2.0.0\n"
    violations = check_requirements_txt(bad_req, "backend/requirements.txt")
    assert any("banned by rule 17" in v.message for v in violations)

    unallowed_req = "flask==3.0.0\n"
    violations = check_requirements_txt(unallowed_req, "backend/requirements.txt")
    assert any("not in allowed backend packages" in v.message for v in violations)

    clean_req = "fastapi\nuvicorn\npydantic\n"
    assert check_requirements_txt(clean_req, "backend/requirements.txt") == []


def test_print_statements() -> None:
    bad_code = "def f():\n    print('hello')\n"
    violations = check_print_statements(bad_code, "backend/core/target/handler.py")
    assert any("print()" in v.message for v in violations)

    allowed_cli = check_print_statements(bad_code, "backend/core/suite/cli.py")
    assert allowed_cli == []

    allowed_demo = check_print_statements(bad_code, "backend/core/target/demo.py")
    assert allowed_demo == []
