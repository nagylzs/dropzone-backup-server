import time
import os
import re
import warnings

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .error import AbortRequest

VALID_PERM_CODES = "W"

HEADER = "# username:upload_dir_prefix:permission_flags:password_hash"


class SecurityManager(object):
    """Manages a list of users.

    Can only be used from a single thread (async server).

    DO NOT USE FROM MULTIPLE THREADS OR PROCESSES.

    You can write into the passwd file on the disk, and it will be reloaded within the number of seconds defined in the
    TTL value below. Otherwise all updates should be done through a security manager object, with this pattern:

    """
    TTL = 10.0  # In seconds

    def __init__(self, passwdfile):
        self.passwdfile = passwdfile
        self._last_loaded = 0
        self._last_mtime = 0
        self._users = None
        self._users = {}
        self._passwords = {}

    def get_users(self) -> dict:
        self._load_all()
        return self._users

    def get_user(self, login):
        users = self.get_users()
        if login in users:
            return users[login]
        else:
            return None

    def _load_all(self):
        now = time.time()
        if self._last_loaded + self.TTL < now:
            mtime = os.stat(self.passwdfile).st_mtime
            if mtime != self._last_mtime:
                self._load_users()
                self._last_mtime = mtime
                self._last_loaded = now

    def _load_users(self):
        # TODO: check permissions of the passwd file and issue a warning when not protected.
        print("Reloading users from %s" % self.passwdfile)
        self._users.clear()
        self._passwords.clear()
        lineno = 0
        for line in open(self.passwdfile, "r"):
            lineno += 1
            line = line.strip()
            if line and not line.startswith("#"):
                login, prefix, perms, *parts = line.split(":")
                pwd = ":".join(parts)
                login = login.strip().lower()
                prefix = prefix.strip()
                login_ok = re.match("[a-z][a-z0-9]*", login)
                prefix_ok = not prefix or re.match(
                    "[a-z][a-z0-9]*(/[a-z][a-z0-9]*)*", prefix) and not prefix.endswith("/")
                if not login_ok:
                    warnings.warn("WARNING: invalid login name '%s' at line %d" % (login, lineno))
                if not prefix_ok:
                    warnings.warn("WARNING: invalid prefix name '%s' at line %d" % (prefix, lineno))
                if login_ok and prefix_ok:
                    self._users[login] = {
                        "name": login,
                        "prefix": prefix,
                        "perms": perms,
                    }
                    self._passwords[login] = pwd

    def _dump_users(self):
        print("Saving users to %s" % self.passwdfile)
        usernames = sorted(self._users.keys())
        with open(self.passwdfile + ".part", "w+") as fout:
            fout.write(HEADER + "\n")
            for username in usernames:
                user = self._users[username]
                # print("???",self._passwords)
                # print("???",self._passwords[username])
                line = "%s:%s:%s:%s" % (
                    username,
                    user["prefix"],
                    user["perms"],
                    self._passwords[username]
                )
                # print(repr(line))
                fout.write(line + "\n")
        bakfile = self.passwdfile + ".bak"
        if os.path.isfile(bakfile):
            os.unlink(bakfile)
        os.rename(self.passwdfile, bakfile)
        os.rename(fout.name, self.passwdfile)

    def check_password(self, login, password) -> bool:
        if not password:
            return False
        user = self.get_user(login)
        if user:
            if not self._passwords[login]:
                return False  # Null password -> disable usedr
            else:
                try:
                    PasswordHasher().verify(self._passwords[login], password)
                    return True
                except VerifyMismatchError:
                    return False
        else:
            return False

    def get_perms(self, login) -> str:
        users = self.get_users()
        if login in users:
            return users[login]["perms"]
        else:
            return ""

    def save_user(self, login, prefix, perms, password):
        # Make sure that we have a fresh db
        self.get_users()
        # Validate parameters
        login = login.strip().lower()
        prefix = prefix.strip()
        login_ok = re.match("[a-z][a-z0-9]*", login)
        prefix_ok = not prefix or re.match(
            "[a-z][a-z0-9]*(/[a-z][a-z0-9]*)*", prefix) and \
                    not prefix.endswith("/")
        if not login_ok:
            raise AbortRequest(400, "Invalid login name '%s'" % login)
        if not prefix_ok:
            raise AbortRequest(400, "Invalid prefix '%s'" % prefix)

        perms = "".join([perm for perm in perms if perm in VALID_PERM_CODES])
        if not password:
            if login in self._passwords:
                password = self._passwords[login]
        else:
            if password and len(password) < 6:
                raise AbortRequest(403, "Minimum password length is 6.")
            elif password == login:
                raise AbortRequest(403, "Password and login must not match.")
            password = PasswordHasher().hash(password)

        if login_ok and prefix_ok:
            # Save to memory
            user = {
                "name": login,
                "prefix": prefix,
                "perms": perms,
            }
            print("Saving user %s" % login)
            self._users[login] = user
            self._passwords[login] = password
            self._dump_users()

    def delete_user(self, login):
        # Make sure that we have a fresh db
        self.get_users()

        # Validate parameters
        login = login.strip().lower()
        login_ok = re.match("[a-z][a-z0-9]*", login)
        if not login_ok:
            raise AbortRequest(400, "Invalid login name '%s'" % login)

        if login in self._users:
            print("Deleting user %s" % login)
            del self._users[login]
            self._dump_users()
        else:
            raise AbortRequest(404, "Cannot delete, user does not exist.")
