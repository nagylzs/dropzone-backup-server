#!/usr/bin/env python3
import sys
import signal
import threading

from winpid import create_pid_file_or_exit

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, StaticFileHandler, url, stream_request_body

from tornadostreamform.multipart_streamer import MultiPartStreamer, TemporaryFileStreamedPart

from .const import *
from .error import AbortRequest
from .security import SecurityManager

MAX_BUFFER_SIZE = 4 * MB  # Max. size loaded into memory!
MAX_BODY_SIZE = 4 * MB  # Max. size loaded into memory!

SIGNAL_NAMES = (dict((k.value, v) for v, k in reversed(sorted(signal.__dict__.items())) if
                     v.startswith('SIG') and not v.startswith('SIG_')))


class Config:
    tmp_suffix: str
    overwrite: bool
    upload_base_dir: str
    anonymous_dir: str
    max_file_size: int
    static_dir_path: str
    security_manager: SecurityManager
    auto_remove_pid_file: bool
    pid_file_path: str
    listen_address: str
    port: int
    auto_create_user_dir: bool


class DroppedFileStreamedPart(TemporaryFileStreamedPart):
    def __init__(self, streamer, headers, upload_dir, config: Config):
        try:
            if config.auto_create_user_dir:
                if not os.path.isdir(upload_dir):
                    os.makedirs(upload_dir)
            super().__init__(streamer, headers, upload_dir, tmp_suffix=config.tmp_suffix)
        except FileNotFoundError:
            raise AbortRequest(500, "Server misconfiguration - could not write to user's upload directory.")
        try:
            self.upload_dir = upload_dir
            self.final_path = os.path.join(upload_dir, self.get_filename())
            if os.path.isfile(self.final_path):
                if config.overwrite:
                    os.unlink(self.final_path)
                else:
                    raise AbortRequest(409, "Conflict - file already exists.")
        except:
            self.release()
            raise

    def finalize(self):
        super().finalize()
        self.move(self.final_path)


class DropFileStreamer(MultiPartStreamer):
    def __init__(self, upload_dir, total, config):
        super().__init__(total)
        self.upload_dir = upload_dir
        self.config = config

    def create_part(self, headers):
        return DroppedFileStreamedPart(self, headers=headers, upload_dir=self.upload_dir, config=self.config)


@stream_request_body
class DropFileHandler(RequestHandler):
    ps: DropFileStreamer
    config: Config

    def initialize(self, config: Config) -> None:
        self.config = config
        super().initialize()

    def get_dest_dir(self):
        username = self.request.headers.get("Username", None)

        if username is not None:
            username = username.strip().lower()
            if not username:
                username = None

        if username is None:
            if not self.config.anonymous_dir:
                raise AbortRequest(401, "Unauthorized - anonymous uploads are not allowed.")
            prefix = self.config.anonymous_dir
        else:
            password = self.request.headers.get("Password", None)
            if not self.config.security_manager.check_password(username, password):
                raise AbortRequest(403, "Invalid username or password.")

            user = self.config.security_manager.get_user(username)
            prefix = user["prefix"]

        if prefix.startswith(os.pardir):
            return prefix
        else:
            return os.path.join(self.config.upload_base_dir, prefix)

    def prepare(self):
        try:
            if self.request.method.lower() not in ["post", "put"]:
                raise AbortRequest(405, "Method Not Allowed - only PUT and POST methods are supported.")

            dir_path = self.get_dest_dir()

            self.request.connection.set_max_body_size(self.config.max_file_size)
            try:
                total = int(self.request.headers.get("Content-Length", "0"))
            except KeyError:
                total = 0  # For any well formed browser request, Content-Length should have a value.
            self.ps = DropFileStreamer(dir_path, total, config=self.config)
        except AbortRequest as e:
            self.set_status(e.status)
            self.set_header("Content-Type", "text/plain")
            self.write(e.message)
            self.finish()

    def data_received(self, chunk):
        try:
            self.ps.data_received(chunk)
        except AbortRequest as e:
            self.ps.release_parts()

            self.set_status(e.status)
            self.set_header("Content-Type", "text/plain")
            self.write(e.message)
            self.finish()

    def post(self):
        try:
            try:
                self.ps.data_complete()
                self.write("OK")
            finally:
                self.ps.release_parts()
        finally:
            self.finish()

    put = post


class Server:
    def __init__(self, config: Config):
        self.config = config
        self.enabled = threading.Event()

    def start(self):
        self.enabled.set()
        create_pid_file_or_exit(self.config.pid_file_path, auto_remove_pid_file=self.config.auto_remove_pid_file)
        handlers = [
            url(r"/upload", DropFileHandler, dict(config=self.config)),
            url(r"/(.*)", StaticFileHandler, dict(path=self.config.static_dir_path, default_filename="index.html")),
        ]
        application = Application(handlers)
        http_server = HTTPServer(
            application,
            max_body_size=MAX_BODY_SIZE,
            max_buffer_size=MAX_BUFFER_SIZE,
        )
        http_server.listen(self.config.port, self.config.listen_address)
        self.setup_signal_handlers()
        self.start_background_threads()
        IOLoop.current().start()

    def stop(self):
        self.enabled.clear()
        ioloop = IOLoop.current()
        ioloop.add_callback(ioloop.stop)

    def setup_signal_handlers(self):
        for sig in [signal.SIGABRT, signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.on_kill)

    def on_kill(self, sig, frame):
        sys.stderr.write("Received %s, exiting...\n" % SIGNAL_NAMES[sig])
        sys.stderr.flush()
        self.stop()

    def start_background_threads(self):
        # TODO: Start background threads in the master process only.
        # EmailConfirmSender(self).start()
        # PasswordResetSender(self).start()
        pass


def main(config: Config):
    Server(config).start()
