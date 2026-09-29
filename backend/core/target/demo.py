import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent.parent
backend_dir = repo_root / "backend"
for path_str in [str(backend_dir), str(repo_root)]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from backend.core.target.assistant import HireAssist


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m core.target.demo <task> <arg> [--no-cache]")
        print("Tasks: summarize, faq, draft, chat")
        sys.exit(1)

    task = sys.argv[1].lower()
    arg = sys.argv[2]
    no_cache = "--no-cache" in sys.argv

    assistant = HireAssist()

    if task in ("summarize", "summarize_candidate"):
        execution = assistant.summarize_candidate(arg, no_cache=no_cache)
    elif task in ("faq", "answer_faq"):
        execution = assistant.answer_faq(arg, no_cache=no_cache)
    elif task in ("draft", "draft_screening_note"):
        execution = assistant.draft_screening_note(arg, no_cache=no_cache)
    elif task in ("chat", "recruiter_chat"):
        execution = assistant.recruiter_chat(arg, no_cache=no_cache)
    else:
        print(f"Unknown task: {task}")
        sys.exit(1)

    print("Reply:")
    print(execution.output_text)
    print("\nTool calls:")
    if execution.tool_calls:
        for call in execution.tool_calls:
            print(f"- {call.name}: {call.args} (status: {call.status})")
    else:
        print("None")
    print(f"\nCached: {execution.raw_completion.cached}")
    print(f"Latency: {execution.raw_completion.latency_ms}ms")


if __name__ == "__main__":
    main()
