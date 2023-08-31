import re
import logging
from pathlib import Path
import argparse
from typing import Union

from .utils import Color

PATTERN = r"(?:|.*\W+)([A-Z]+-[0-9]+)\W*"
THRESHOLD_FILE_SIZE_BYTES = 3 * (1024 ** 3)

def extract_code(pattern, s: str) -> Union[None, str]:
    g = pattern.match(s)
    if g is not None:
        return g.group(1)
    return None


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s [%(levelname)7s]  %(message)s"
                        , level=logging.DEBUG
                        , datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser(description="Kat utilites")
    parser.add_argument("path", type=str, help="Input Kat folder")
    parser.add_argument("--target", type=str, required=True, help="Target folder")
    parser.add_argument("--prefix", type=str, help="Prefix for file", default="")
    parser.add_argument("--suffix", type=str, help="Suffix for file", default="")

    args = parser.parse_args()
    base_folder = args.path
    target_folder = args.target
    prefix = args.prefix
    suffix = args.suffix

    base_path = Path(base_folder)
    target_path = Path(target_folder)

    if not base_path.is_dir():
        raise OSError(f"ERROR: {base_folder} is not exist!")

    if not target_path.is_dir():
        raise OSError(f"ERROR: {target_folder} is not exist!")

    logging.info(f"InputFolder: {base_path.absolute()}")
    logging.info(f"OutFolder: {target_path.absolute()}")

    pattern = re.compile(PATTERN)

    for path in base_path.glob("**/*.mp4"):
        base_name = path.name
        ext = path.suffix

        if path.lstat().st_size < THRESHOLD_FILE_SIZE_BYTES:
            logging.warning(">>> {0} size less than threshold...{1}".format(str(path) ,Color.yellow("SKIPPING")))
            continue

        code = extract_code(pattern, base_name)
        full_name = f"{base_folder}/{path.name}"

        if code is not None:
            dirname = target_path / code
            out = dirname / (prefix + code + ext + suffix)

            if not dirname.is_dir():
                dirname.mkdir()

            path.rename(out)
            logging.info(">>> '{0}' rename to {1}...{2}".format(str(path), out, Color.green("OK")))
        else:
            logging.warning(">>> '{0}' not matched...{1}".format(str(path), Color.yellow("SKIPPING")))

