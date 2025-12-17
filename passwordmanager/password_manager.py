import json
import os
import getpass
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken
import base64
import secrets

VAULT_FILE = "vault.json"
KDF_ITERATIONS = 390_000  # strong default (similar order to modern recommendations)


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8")


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def load_or_create_vault() -> Dict[str, Any]:
    if not os.path.exists(VAULT_FILE):
        # Create empty encrypted vault
        salt = secrets.token_bytes(16)
        vault = {
            "version": 1,
            "kdf": {"name": "PBKDF2HMAC-SHA256", "iterations": KDF_ITERATIONS, "salt": b64e(salt)},
            "data": None,  # encrypted blob
        }
        with open(VAULT_FILE, "w", encoding="utf-8") as f:
            json.dump(vault, f, indent=2)
    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_vault(vault: Dict[str, Any]) -> None:
    with open(VAULT_FILE, "w", encoding="utf-8") as f:
        json.dump(vault, f, indent=2)


def decrypt_entries(vault: Dict[str, Any], master_password: str) -> Dict[str, Dict[str, str]]:
    salt = b64d(vault["kdf"]["salt"])
    key = derive_key(master_password, salt)
    fernet = Fernet(key)

    if vault["data"] is None:
        return {}

    try:
        plaintext = fernet.decrypt(vault["data"].encode("utf-8"))
    except InvalidToken:
        raise ValueError("Wrong master password (or vault corrupted).")

    entries = json.loads(plaintext.decode("utf-8"))
    if not isinstance(entries, dict):
        raise ValueError("Vault data invalid.")
    return entries


def encrypt_entries(vault: Dict[str, Any], master_password: str, entries: Dict[str, Dict[str, str]]) -> None:
    salt = b64d(vault["kdf"]["salt"])
    key = derive_key(master_password, salt)
    fernet = Fernet(key)

    plaintext = json.dumps(entries, ensure_ascii=False).encode("utf-8")
    token = fernet.encrypt(plaintext).decode("utf-8")
    vault["data"] = token


def prompt_master_password(confirm_if_new: bool) -> str:
    pw = getpass.getpass("Master password: ")
    if confirm_if_new:
        pw2 = getpass.getpass("Confirm master password: ")
        if pw != pw2:
            raise ValueError("Passwords do not match.")
    if len(pw) < 10:
        print("Note: Consider a longer master password (10+ chars).")
    return pw


def menu():
    print("\n=== Password Manager (Local Encrypted Vault) ===")
    print("1) Add entry")
    print("2) Get entry")
    print("3) List services")
    print("4) Delete entry")
    print("5) Change master password")
    print("0) Quit")


def main():
    vault = load_or_create_vault()
    is_new = vault["data"] is None

    print(f"Vault file: {VAULT_FILE}")
    if is_new:
        print("No entries yet. You'll set a master password now.")
        master = prompt_master_password(confirm_if_new=True)
        entries: Dict[str, Dict[str, str]] = {}
        encrypt_entries(vault, master, entries)
        save_vault(vault)
        print("Vault initialized.")
    else:
        master = prompt_master_password(confirm_if_new=False)

    # Load entries
    entries = decrypt_entries(vault, master)

    while True:
        menu()
        choice = input("Choose: ").strip()

        try:
            if choice == "1":
                service = input("Service name (e.g. gmail): ").strip().lower()
                if not service:
                    raise ValueError("Service name required.")
                username = input("Username/email: ").strip()
                password = getpass.getpass("Password (hidden): ")
                note = input("Note (optional): ").strip()

                entries[service] = {"username": username, "password": password, "note": note}
                encrypt_entries(vault, master, entries)
                save_vault(vault)
                print("Saved.")

            elif choice == "2":
                service = input("Service to get: ").strip().lower()
                item = entries.get(service)
                if not item:
                    print("Not found.")
                else:
                    print("\n--- Entry ---")
                    print(f"Service : {service}")
                    print(f"Username: {item.get('username','')}")
                    print(f"Password: {item.get('password','')}")
                    n = item.get("note", "")
                    if n:
                        print(f"Note    : {n}")
                    print("-----------\n")

            elif choice == "3":
                services = sorted(entries.keys())
                if not services:
                    print("No entries.")
                else:
                    print("\nSaved services:")
                    for s in services:
                        print(" -", s)

            elif choice == "4":
                service = input("Service to delete: ").strip().lower()
                if service in entries:
                    del entries[service]
                    encrypt_entries(vault, master, entries)
                    save_vault(vault)
                    print("Deleted.")
                else:
                    print("Not found.")

            elif choice == "5":
                # Change master password by decrypting then re-encrypting with new key
                print("Changing master password.")
                new_master = prompt_master_password(confirm_if_new=True)
                encrypt_entries(vault, new_master, entries)
                save_vault(vault)
                master = new_master
                print("Master password updated.")

            elif choice == "0":
                print("Bye!")
                return
            else:
                print("Invalid choice.")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
