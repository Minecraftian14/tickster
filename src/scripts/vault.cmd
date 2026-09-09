@# 2>nul & xonsh %~f0 %~dp0 %* & exit /b %errorlevel%

import base64
import difflib
import os
import secrets
import shutil
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from pathlib import Path 
from dotenv import load_dotenv

load_dotenv()


_VAULT_FILENAME = "docs.txt"
_FORMAT = b"VAULT1"


def _get_cipher(_key):
    """Create an AES-SIV cipher."""
    if isinstance(_key, str): _key = _key.encode("ascii")
    if len(_key) != 64:
        try: _key = base64.urlsafe_b64decode(_key)
        except Exception: pass
    if len(_key) != 64: raise ValueError("AES-SIV requires a 64-byte key (512 bits) for AES-256-SIV.")
    return AESSIV(_key)

def _encrypt_record(cipher, record):
    """Encrypt a record and return printable ASCII."""
    return base64.urlsafe_b64encode(cipher.encrypt(record, [])).decode("ascii")

def _decrypt_record(cipher, record):
    """Decrypt a printable ASCII record."""
    return cipher.decrypt(base64.urlsafe_b64decode(record), [])

def print_help():
    print(
        "Usage:\n"
        "  vault <operation>\n"
        "\n"
        "Description:\n"
        "  Encrypts, decrypts, and compares the project's vault files.\n"
        "\n"
        "Operations:\n"
        "  pull\n"
        "      Decrypt .envault/docs.txt into the plaintext docs/vault directory.\n"
        "      Any existing docs/vault directory is deleted first.\n"
        "\n"
        "  push\n"
        "      Encrypt the contents of docs/vault into .envault/docs.txt.\n"
        "      Any existing docs/envault directory is replaced.\n"
        "\n"
        "  diff\n"
        "      Compare the plaintext docs/vault directory with the encrypted\n"
        "      contents of docs/envault/docs.txt and display any differences.\n"
        "\n"
        "  key\n"
        "      Generate and print a new random vault encryption key.\n"
        "\n"
        "Options:\n"
        "  -h, --help, /?\n"
        "      Show this help message.\n"
        "\n"
        "Environment:\n"
        "  VAULT_KEY\n"
        "      Required for pull, push, and diff.\n"
        "      The key must be a valid 64-byte (512-bit) AES-SIV key, either\n"
        "      provided directly or as URL-safe Base64.\n"
    )

def pull_vault(_path, _key):
    base = Path(_path)
    vault = (base / "../../docs/vault").resolve()
    envault = (base / "../../docs/envault").resolve()
    docs = envault / _VAULT_FILENAME

    answer = input(f"WARNING: Any changes in '{vault}' will be deleted. Continue? [y/N] ")
    if answer != "y": return

    if vault.exists(): shutil.rmtree(vault)
    vault.mkdir(parents=True)

    if not docs.exists(): return

    cipher = _get_cipher(_key)
    current_file, current_output = None, None

    try:
        with docs.open("r", encoding="ascii", newline="\n") as src:
            for line_number, encoded in enumerate(src, 1):
                encoded = encoded.rstrip("\r\n")

                if not encoded: raise ValueError(f"Empty record at line {line_number} in {docs}")

                try: record = _decrypt_record(cipher, encoded)
                except Exception as exc:
                    raise ValueError(f"Could not decrypt record at line {line_number}") from exc

                if record == _FORMAT: continue

                if record.startswith(b"FILE\0"):
                    if current_output is not None:
                        current_output.close()

                    relative_path = record[5:].decode("utf-8")
                    relative = Path(relative_path)

                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError(f"Invalid vault path: {relative_path!r}")

                    current_file = vault / relative
                    current_file.parent.mkdir(parents=True, exist_ok=True)

                    current_output = current_file.open("w", encoding="utf-8", newline="")

                elif record.startswith(b"LINE\0"):
                    if current_output is None:
                        raise ValueError(f"LINE record before FILE record at line {line_number}")

                    # The original newline, if any, is part of the
                    # encrypted record, so it is reproduced exactly.
                    content = record[5:].decode("utf-8")
                    current_output.write(content)

                else: raise ValueError(f"Unknown record at line {line_number}")

    finally:
        if current_output is not None:
            current_output.close()

def push_vault(_path, _key):
    base = Path(_path)
    vault = (base / "../../docs/vault").resolve()
    envault = (base / "../../docs/envault").resolve()
    docs = envault / _VAULT_FILENAME

    if envault.exists(): shutil.rmtree(envault)
    envault.mkdir(parents=True)

    cipher = _get_cipher(_key)

    with docs.open("w", encoding="ascii", newline="\n") as dst:
        dst.write(_encrypt_record(cipher, _FORMAT) + "\n")

        if not vault.exists(): return

        # Sort files by relative path so the output is deterministic.
        files = sorted(
            (path for path in vault.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(vault).as_posix(),
        )

        for source in files:
            relative_path = source.relative_to(vault).as_posix()

            file_record = b"FILE\0" + relative_path.encode("utf-8")
            dst.write(_encrypt_record(cipher, file_record) + "\n")

            with source.open("r", encoding="utf-8", newline="") as src:
                for content in src:
                    line_record = b"LINE\0" + content.encode("utf-8")
                    dst.write(_encrypt_record(cipher, line_record) + "\n")

def diff_vault(_path, _key):
    base = Path(_path)
    vault = (base / "../../docs/vault").resolve()
    envault = (base / "../../docs/envault").resolve()
    docs = envault / _VAULT_FILENAME

    if not docs.exists(): return

    cipher = _get_cipher(_key)

    encrypted_files = {}
    current_file = None

    with docs.open("r", encoding="ascii", newline="\n") as src:
        for line_number, encoded in enumerate(src, 1):
            encoded = encoded.rstrip("\r\n")

            if not encoded: raise ValueError(f"Empty record at line {line_number} in {docs}")

            try: record = _decrypt_record(cipher, encoded)
            except Exception as exc:
                raise ValueError(f"Could not decrypt record at line {line_number}") from exc

            if record == _FORMAT: continue

            if record.startswith(b"FILE\0"):
                relative_path = record[5:].decode("utf-8")
                current_file = relative_path
                encrypted_files[current_file] = []

            elif record.startswith(b"LINE\0"):
                if current_file is None:
                    raise ValueError(f"LINE record before FILE record at line {line_number}")

                encrypted_files[current_file].append(record[5:].decode("utf-8"))

            else: raise ValueError(f"Unknown record at line {line_number}")

    # Read the plaintext vault.
    plaintext_files = {}

    if vault.exists():
        for source in vault.rglob("*"):
            if not source.is_file():
                continue

            relative_path = source.relative_to(vault).as_posix()

            with source.open("r", encoding="utf-8", newline="") as src:
                plaintext_files[relative_path] = src.read()

    # Compare the union of both sets of paths.
    all_paths = sorted(set(plaintext_files) | set(encrypted_files))

    differences_found = False

    for relative_path in all_paths:
        vault_content = plaintext_files.get(relative_path, "")
        envault_content = "".join(encrypted_files.get(relative_path, []))

        if vault_content == envault_content: continue

        differences_found = True

        # A file that exists only in vault is new.
        if relative_path not in encrypted_files:
            old = []
            new = vault_content.splitlines(keepends=True)

        # A file that exists only in envault was deleted from vault.
        elif relative_path not in plaintext_files:
            old = envault_content.splitlines(keepends=True)
            new = []

        else:
            old = envault_content.splitlines(keepends=True)
            new = vault_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old,
            new,
            fromfile=f"envault/{relative_path}",
            tofile=f"vault/{relative_path}",
            lineterm="",
        )

        print()
        print("\n".join(diff))

    if not differences_found:
        print("Vault is unchanged.")

def gen_key():
    key = base64.urlsafe_b64encode(secrets.token_bytes(64))
    print(key.decode("ascii"))


args = sys.argv[1:]
path = args.pop(0)

if len(args) == 0:
    print("Please select an operation:")
    print("  vault pull    decrypts envault/ to vault/")
    print("  vault push    encrypts vault/ to envault/")
    print("  vault diff    compares vault/ to envault/")
    print("  vault key     generate a new key")
    exit()

oprn = args.pop(0)
ekey = os.getenv("VAULT_KEY")

if ekey is None and oprn != "key":
    print("No VAULT_KEY defined!")
    exit()

match oprn:
    case "/?" | "-h" | "--help": print_help()
    case "pull": pull_vault(path, ekey)
    case "push": push_vault(path, ekey)
    case "diff": diff_vault(path, ekey)
    case "key":  gen_key()
    case _: print(f"{oprn} is not a valid operation")    
