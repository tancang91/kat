import re
import logging
from typing import Union
from typing import Tuple, List
from argparse import Namespace
from pathlib import Path

from .utils import Color
from .ffmpeg import Encoder

CODE_PATTERN = r"(?:|.*\W+)([A-Z]+-[0-9]+)\W*"
THRESHOLD_FILE_SIZE_BYTES = 3 * (1024 ** 3)
MB_SIZE = 1024 ** 2
TMP_DIR_NAME = "_tmp"

def _extract_code(pattern, s: str) -> Union[None, str]:
    g = pattern.match(s)
    if g is not None:
        return g.group(1)
    return None

async def encode_service(args: Namespace):
    src = Path(args.input)
    dest = Path(args.out)
    recursive = args.recursive
    limit = args.max

    pairs: List[Tuple] = []

    if not recursive:
        if dest.is_dir():
            raise ValueError(f"Output {dest} folder not allowed in non-recursive mode")
        pairs.append((src, dest))
        temp_dir_path = dest.parent / TMP_DIR_NAME

    else:
        if not src.is_dir():
            raise ValueError(f"ERROR: Input {src} must be folder in recursive mode!!")
        elif not dest.is_dir():
            raise ValueError(f"ERROR: Output {dest} must be folder in recursive mode!!")

        logging.info("Start scanning...")
        pat = re.compile(CODE_PATTERN)
        for spath in src.glob("**/*.raw"):
            code = _extract_code(pat, spath.name)
            if code is None:
                continue

            dest_path = dest / (code + ".mp4")
            pairs.append((spath, dest_path))
            logging.debug(f"Source: {spath}, Dest: {dest_path}")

        temp_dir_path = dest / TMP_DIR_NAME

    if not temp_dir_path.is_dir():
        temp_dir_path.mkdir()

    encoder = Encoder()
    for (s, d) in pairs:
        if limit <= 0:
            break
        temp_proc_path = temp_dir_path / d.name
        if d.is_file():
            yes = str(input(f"{d} already exist!\nWould you like to overwrite [y/N]: "))
            if yes.strip() not in ("y", "Y"):
                continue
        await encoder.encode_h265(s, temp_proc_path)
        temp_proc_path.rename(d)
        limit -= 1

def rename_service(args: Namespace):
    base_folder = args.input
    target_folder = args.out
    prefix = args.prefix
    suffix = args.suffix

    base_path = Path(base_folder)
    target_path = Path(target_folder)

    if not base_path.is_dir():
        raise OSError(f"ERROR: {base_folder} is not exist!")

    if not target_path.is_dir():
        raise OSError(f"ERROR: {target_folder} is not exist!")

    logging.debug(f"InputFolder: {base_path.absolute()}")
    logging.debug(f"OutFolder: {target_path.absolute()}")

    pattern = re.compile(CODE_PATTERN)

    for path in base_path.glob("**/*.mp4"):
        base_name = path.name
        ext = path.suffix

        if path.lstat().st_size < THRESHOLD_FILE_SIZE_BYTES:
            logging.warning(">>> {0} size less than threshold...{1}" \
                                .format(str(path) ,Color.yellow("SKIPPING"))
                        )
            continue

        code = _extract_code(pattern, base_name)

        if code is not None:
            dirname = target_path / code
            out = dirname / (prefix + code + ext + suffix)

            if not dirname.is_dir():
                dirname.mkdir()

            path.rename(out)
            logging.info(">>> [{2:<10}] '{0}' rename to {1}" \
                            .format(str(path), out, Color.green("OK"))
                    )
        else:
            logging.warning(">>> '[{1:<10}] {0}' not matched" \
                                .format(str(path), Color.yellow("SKIPPING"))
                        )

    logging.info("All done. Thanks for using my service")

def mv_service(args: Namespace):
    in_path = Path(args.input)
    out_path = Path(args.out)

    if not in_path.exists():
        raise OSError(f"ERROR: {in_path} is not exist!")

    if not out_path.is_dir():
        raise ValueError(f"ERROR: Output {out_path} must be folder!!")

    pairs: List[Tuple] = []
    pat = re.compile(CODE_PATTERN)

    if in_path.is_dir():
        for path in in_path.glob("*.mp4"):
            if path.stat().st_size < (100 * MB_SIZE):
                logging.warning("[{1:<10}] {0} size too small (less than 100mb)" \
                                    .format(str(path), Color.yellow("SKIPPING"))
                            )
                continue

            if (code := _extract_code(pat, path.name)) is not None:
                dest_media_path = out_path / code / (code + ".mp4")
                pairs.append((path, dest_media_path))
    elif in_path.is_file() and in_path.suffix == ".mp4":
        if in_path.stat().st_size < (100 * MB_SIZE):
            logging.warning("[{1:<10}] {0} size too small (less than 100mb)" \
                                .format(str(in_path), Color.yellow("SKIPPING"))
                        )
        elif (code := _extract_code(pat, in_path.name)) is not None:
            dest_media_path = out_path / code / (code + ".mp4")
            pairs.append((in_path, dest_media_path))
    else:
        return

    for (s, d) in pairs:
        if d.is_file():
            logging.info("[{1:<10}] {0} already exist" \
                            .format(str(d), Color.yellow("SKIPPING"))
                    )
        else:
            if not d.parent.is_dir():
                d.parent.mkdir()
            s.rename(d)
            logging.info("[{1:<10}] Move to {0}".format(str(d), Color.green("OK")))

