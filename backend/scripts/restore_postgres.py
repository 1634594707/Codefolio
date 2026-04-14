import argparse
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a PostgreSQL backup for Codefolio.")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL connection URL.")
    parser.add_argument("--input", required=True, help="Input dump file path produced by pg_dump.")
    parser.add_argument("--clean", action="store_true", help="Drop database objects before restoring.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        raise SystemExit("pg_restore not found in PATH. Install PostgreSQL client tools first.")

    parsed = urlparse(args.postgres_url)
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Backup file not found: {input_path}")

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    command = [
        pg_restore,
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
    ]
    if args.clean:
        command.extend(["--clean", "--if-exists"])
    command.append(str(input_path))

    subprocess.run(command, check=True, env=env)
    print(f"Restore completed from {input_path}")


if __name__ == "__main__":
    main()
