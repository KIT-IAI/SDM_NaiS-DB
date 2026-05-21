from __future__ import annotations

import subprocess
import sys

from core.build_registry import BUILD_STEPS



def _select_steps(requested_names: set[str] | None):
    if not requested_names:
        return BUILD_STEPS

    selected = [step for step in BUILD_STEPS if step.module_name in requested_names]
    missing = requested_names - {step.module_name for step in selected}
    if missing:
        raise SystemExit(f"Unknown build steps: {', '.join(sorted(missing))}")

    return tuple(selected)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    requested_names = set(argv) if argv else None
    steps = _select_steps(requested_names)

    for step in steps:
        print(f"Running {step.module_name} ({step.label})")
        subprocess.run([sys.executable, "-m", f"scripts.{step.module_name}"], check=True)

    print("Build completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
