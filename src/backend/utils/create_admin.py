"""Interactively generate an Argon2id hash for the local administrator.

Run from the repository root:
    python -m src.backend.utils.create_admin

The script prints environment-variable assignments only. It never writes a
password or hash into project files automatically.
"""

import getpass

from argon2 import PasswordHasher


def main() -> None:
    username = input("Administrator username: ").strip()
    if not username or len(username) > 128:
        raise SystemExit("Username must contain 1 to 128 characters.")

    password = getpass.getpass("Administrator password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Use an administrator password with at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    password_hash = PasswordHasher().hash(password)
    print("\nAdd these lines to your local .env file (keep that file private):")
    print(f"ADMIN_USERNAME={username}")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")


if __name__ == "__main__":
    main()
