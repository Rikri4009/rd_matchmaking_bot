import csv
import os
import json
from csv import DictReader
from typing import Literal


def get_path(dirname: str):
    """
    Returns the path to a ``dirname`` relative to the project's parent folder.
    """

    cur_dirs = os.path.dirname(__file__).split(os.sep)
    src_index = cur_dirs.index("src")
    target_dirs = dirname.split(os.sep)

    return f"{os.sep}".join(cur_dirs[:src_index] + target_dirs)


def read_file(filepath: str, filename: str) -> dict | DictReader:
    """
    Reads the contents of ``filename`` at ``filepath``.

    Supports ``.json`` and ``.csv`` extensions only.
    """

    ext = filename.split(".")[1]

    if ext not in ["json", "csv"]:
        raise TypeError("Invalid extension")

    with open(filepath + os.sep + filename, "r", encoding='utf-8') as in_file:
        if ext == "json":
            return json.load(in_file)
        elif ext == "csv":
            reader = csv.DictReader(in_file)
            return list(reader)
        else:
            print("unsupported file extension")
            return None


def write_json(obj: dict, filepath: str, filename: str):
    json_object = json.dumps(obj, indent=4)

    with open(filepath + os.sep + filename, "w") as out_file:
        out_file.write(json_object)