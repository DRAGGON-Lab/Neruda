"""Create a standalone Neruda article or slides project in an existing directory."""

import argparse
from contextlib import ExitStack
import errno
import os
from pathlib import Path
import re
import signal
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
COMMON = {
    ".gitignore": "templates/common/.gitignore",
    "AGENTS.md": "templates/common/AGENTS.md",
    "LICENSE": "LICENSE",
    "scripts/latex.py": "scripts/latex.py",
    "tools/texlive-lock.json": "tools/texlive-lock.json",
    "src/neruda.sty": "tex/neruda.sty",
    "src/bib/references.bib": "templates/common/src/bib/references.bib",
}
PROFILES = {
    "article": (
        "README.md",
        "src/main.tex",
        "src/metadata.tex",
        "src/sections/introduction.tex",
        "src/sections/mathematical-concepts.tex",
        "src/sections/reproducibility.tex",
    ),
    "slides": (
        "README.md",
        "src/main.tex",
        "src/handout.tex",
        "src/presentation.tex",
        "src/metadata.tex",
        "src/frames/mapping.tex",
        "src/frames/check.tex",
        "src/frames/documentation.tex",
    ),
}
PROFILE_STYLES = {
    "article": "neruda-article.sty",
    "slides": "beamerthemeNeruda.sty",
}
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class InvalidInput(Exception):
    """The requested destination is invalid or already exists."""


def open_directory(stack, path, parent=None):
    descriptor = os.open(path, DIRECTORY_FLAGS, dir_fd=parent)
    stack.callback(os.close, descriptor)
    return descriptor


def open_parent(stack, argument):
    if not argument:
        raise InvalidInput("parent path is required")
    path = Path(argument)
    if ".." in path.parts:
        raise InvalidInput("parent path must not contain '..'")
    path = Path.cwd() / path
    try:
        descriptor = open_directory(stack, path.anchor)
        for part in path.parts[1:]:
            descriptor = open_directory(stack, part, descriptor)
    except OSError as error:
        if error.errno in (errno.ENOENT, errno.ENOTDIR, errno.ELOOP):
            raise InvalidInput(f"parent must be an existing directory without symlinks: {path}") from error
        raise
    return path, descriptor


def bundled_files(profile, root):
    """Read and validate the entire allowlist before making any output."""
    sources = COMMON | {path: f"templates/{profile}/{path}" for path in PROFILES[profile]}
    style = PROFILE_STYLES[profile]
    sources[f"src/{style}"] = f"tex/{style}"
    files = {}
    for target, source in sources.items():
        try:
            with ExitStack() as stack:
                directory = open_directory(stack, root)
                path = Path(source)
                for part in path.parts[:-1]:
                    directory = open_directory(stack, part, directory)
                descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     dir_fd=directory)
                stack.callback(os.close, descriptor)
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise OSError("expected a regular file")
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    files[Path(target)] = stream.read()
        except OSError as error:
            raise OSError(f"invalid bundled source {source}: {error}") from error
    return files


def remove_created(entries):
    errors = []
    for directory, name, identity in reversed(entries):
        try:
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if not os.path.samestat(identity, current):
                errors.append(f"{name} was replaced")
            elif stat.S_ISDIR(identity.st_mode):
                os.rmdir(name, dir_fd=directory)
            else:
                os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            continue
        except OSError as error:
            errors.append(str(error))
    return errors


def write_file(descriptor, contents):
    with os.fdopen(descriptor, "wb", closefd=False) as stream:
        stream.write(contents)


def open_created_directory(stack, parent, name, created):
    identity = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISDIR(identity.st_mode):
        raise OSError(f"new directory was replaced: {name}")
    created.append((parent, name, identity))
    descriptor = open_directory(stack, name, parent)
    if not os.path.samestat(identity, os.fstat(descriptor)):
        raise OSError(f"new directory was replaced: {name}")
    return descriptor


def populate(stack, directory, files, created, checkpoint):
    directories = {Path("."): directory}
    for path, contents in files.items():
        checkpoint()
        for folder in reversed(path.parents):
            if folder not in directories:
                parent = directories[folder.parent]
                os.mkdir(folder.name, dir_fd=parent)
                directories[folder] = open_created_directory(stack, parent, folder.name, created)
        parent = directories[path.parent]
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o666, dir_fd=parent)
        try:
            created.append((parent, path.name, os.fstat(descriptor)))
            write_file(descriptor, contents)
        finally:
            os.close(descriptor)
    checkpoint()


def create_project(parent, destination, files, checkpoint):
    name = destination.name
    checkpoint()
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)
    except FileExistsError as error:
        raise InvalidInput(f"destination already exists: {destination}") from error

    with ExitStack() as stack:
        created = []
        try:
            directory = open_created_directory(stack, parent, name, created)
            populate(stack, directory, files, created, checkpoint)
        except (OSError, KeyboardInterrupt) as error:
            failures = remove_created(created)
            if failures or not created:
                detail = "; ".join(failures) or "could not identify the reserved directory"
                raise OSError(f"{error}; partial output may remain at {destination}: {detail}") from error
            raise


def main(argv=None, *, root=ROOT, checkpoint=lambda: None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("name", help="Lowercase ASCII letters and digits separated by single hyphens")
    parser.add_argument("--parent", required=True, help="Existing directory without symlink components")
    args = parser.parse_args(argv)
    if not NAME.fullmatch(args.name):
        parser.error("name must be lowercase ASCII kebab-case")

    try:
        with ExitStack() as stack:
            parent, directory = open_parent(stack, args.parent)
            destination = parent / args.name
            create_project(directory, destination, bundled_files(args.profile, root), checkpoint)
    except InvalidInput as error:
        parser.error(str(error))
    except (OSError, KeyboardInterrupt) as error:
        print(f"scaffold: {error or 'interrupted'}", file=sys.stderr)
        return 1

    print(destination)
    return 0


if __name__ == "__main__":
    interrupted = None

    def request_stop(signum, _frame):
        # Defer interruption until the current filesystem operation is journaled.
        global interrupted
        interrupted = signum

    def check_interrupt():
        if interrupted is not None:
            raise OSError(f"interrupted by {signal.Signals(interrupted).name}")

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    sys.exit(main(checkpoint=check_interrupt))
