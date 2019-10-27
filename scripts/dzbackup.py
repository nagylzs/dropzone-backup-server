import argparse
import getpass
from dropzone_backup_server.const import *
from dropzone_backup_server.server import main
from dropzone_backup_server.security import SecurityManager

MAX_STREAMED_SIZE = 1 * TB  # Max. size streamed in one request
VALID_ACTIONS = ["serve", "adduser", "deluser"]

parser = argparse.ArgumentParser(description='Dropzone-Backup Server')

parser.add_argument("action", default="serve", help="Action to be performed: %s" % VALID_ACTIONS)
parser.add_argument("-p", "--port", dest='port', metavar="PORT",
                    type=int, default=8888,
                    help="Port number to listen on"
                    )
parser.add_argument("-l", "--listen", dest='listen_address', metavar="LISTEN_ADDRESS",
                    type=str, default="",
                    help="Address to listen on. Default is to listen on all addresses."
                    )
parser.add_argument("-m", "--max-file-size", dest='max_file_size', metavar="MAX_STREAMED_SIZE",
                    type=int, default=MAX_STREAMED_SIZE,
                    help="Maximum file size to be accepted. Defaults to 1*TB"
                    )
parser.add_argument("--pidfile", dest='pid_file_path', metavar="PIDFILE",
                    default="dropzone-backup-server.pid",
                    help="Filename where the pid of the process should be written."
                    )
parser.add_argument("--auto-remove-pid-file", dest='auto_remove_pid_file', action="store_true", default=False,
                    help="Auto remove the pid file (useful for testing, when psutil is not available)."
                    )
parser.add_argument("--static-dir", dest='static_dir_path', metavar="STATIC_DIR_PATH",
                    default=STATIC_DIR_PATH,
                    help="Path to a directory that will serve static files, starting with 'index.html'. "
                         "The default static file dir contains a simple file upload form that can be used to "
                         "upload files from a browser. (%s)" % STATIC_DIR_PATH
                    )

parser.add_argument("--upload-base-dir", dest='upload_base_dir', metavar="UPLOAD_BASE_DIR",
                    default=None,
                    help="Path to a directory that will store files uploaded for all users. "
                         "When relative paths are given for a user, then they will be relative to this directory."
                    )
parser.add_argument("--anonymous-dir", dest='anonymous_dir', metavar="ANONYMOUS_DIR",
                    default=None,
                    help="Path to a directory that will store files uploaded by anonymous users. "
                         "When not given, anonymous uploads will be disabled. When relative path is given,"
                         "it will be relative to what was given in --upload-dir."
                    )
parser.add_argument("--tmp-suffix", dest='tmp_suffix', metavar="TMP_SUFFIX",
                    default=".~tmp",
                    help="Suffix to be used for temporary files (while streaming incoming data)"
                    )
parser.add_argument("--overwrite", dest='overwrite', default=False, action="store_true",
                    help="Allow overwrite files."
                    )
parser.add_argument("--passwdfile", dest='passwdfile', metavar="PASSWD_FILE",
                    default="passwd",
                    help="Passwd file for authenticating users"
                    )
parser.add_argument("-u", "--username", dest='username', metavar="USER_NAME",
                    default=None, help="Username  (for adding/updating users).")
parser.add_argument("--password", dest='password', metavar="PASSWORD",
                    default=None, help="Password  (for adding/updating users).")
parser.add_argument("--prefix", dest='prefix', metavar="PREFIX",
                    default="",
                    help="Prefix dir (for adding/updating users). When relative path is specified, then it is "
                         "relative to --upload-base dir.")

parser.add_argument("--auto-create-user-dirs", dest='auto_create_user_dir', action="store_true", default=False,
                    help="Automatically create user upload directories if they don't exist. (Can be dangerous"
                         " when absolute upload dirs are specified!)"
                    )

parser.add_argument("-v", "--verbose", dest='verbose', action="store_true", default=False,
                    help="Change log level from WARNING to INFO."
                    )
parser.add_argument("-d", "--debug", dest='debug', action="store_true", default=False,
                    help="Change log level from INFO to DEBUG."
                    )

args = parser.parse_args()

if args.action not in VALID_ACTIONS:
    parser.error("Invalid action, must be in: %s" % VALID_ACTIONS)

security_manager = SecurityManager(args.passwdfile)

if args.action == "adduser":
    if not os.path.isfile(args.passwdfile):
        with open(args.passwdfile, "w+") as fout:
            pass

    username = args.username
    password = args.password
    if not username:
        parser.error("You must specify --username for the adduser action.")
    if password is None:
        password = getpass.getpass("Password:")
    if not password:
        parser.error("Invalid empty password.")
    perms = "W"
    security_manager.save_user(username, args.prefix, perms, password)
elif args.action == "deluser":
    username = args.username
    if not username:
        parser.error("You must specify --username for the deluser action.")
    security_manager.delete_user(username)
else:
    if not args.upload_base_dir:
        parser.error("--upload-base-dir must be given.")

    args.security_manager = security_manager
    main(args)
