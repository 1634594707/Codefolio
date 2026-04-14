import argparse
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PostgreSQL backup for Codefolio.")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL connection URL.")
    parser.add_argument("--output", required=True, help="Output dump file path, usually ending with .dump.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise SystemExit("pg_dump not found in PATH. Install PostgreSQL client tools first.")

    parsed = urlparse(args.postgres_url)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    command = [
        pg_dump,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host",
        parsed.hostname or "localhost",
        "--port",
        str(parsed.port or 5432),
        "--username",
        parsed.username or "",
        "--dbname",
        (parsed.path or "/")[1:],
        "--file",
        str(output_path),
    ]
    subprocess.run(command, check=True, env=env)
    print(f"Backup written to {output_path}")


if __name__ == "__main__":
    main()
