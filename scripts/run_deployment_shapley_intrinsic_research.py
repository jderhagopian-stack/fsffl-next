from pathlib import Path

_parts = Path(__file__).with_name("_deployment_shapley_parts")
_source = "".join(((_parts / f"part{i:02d}.txt").read_text(encoding="utf-8")) for i in range(1, 9))
exec(compile(_source, str(Path(__file__)), "exec"), globals(), globals())
