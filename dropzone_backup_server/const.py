import os

MB = 1024 * 1024
GB = 1024 * MB
TB = 1024 * GB

MY_DIR = os.path.split(os.path.abspath(__file__))[0]
STATIC_DIR_PATH = os.path.join(MY_DIR, "static")
