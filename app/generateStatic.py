import os
import shutil
import time

# Set CWD to script location
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

os.environ["GENERATING_STATIC"] = "1"

import main  # flask app

OUTPUT_DIRECTORY = "dist"

if os.path.exists(OUTPUT_DIRECTORY):
    shutil.rmtree(OUTPUT_DIRECTORY, ignore_errors=True)  # Clear pre-existing

time.sleep(0.5)

if not os.path.exists:
    os.mkdir(OUTPUT_DIRECTORY)

# Copy content

shutil.copytree("content", os.path.join(OUTPUT_DIRECTORY, "content"))

# Iter dirs and find those that do not have any PDFs in them

for dir in [name for name in os.listdir(os.path.join(OUTPUT_DIRECTORY, "content")) if os.path.isdir(os.path.join(os.path.join(OUTPUT_DIRECTORY, "content"), name))]:
    for root, dirs, files in os.walk(os.path.join(OUTPUT_DIRECTORY, "content")):
        for currentFile in files:
            if not currentFile.lower().endswith(".pdf"):
                os.remove(os.path.join(root, currentFile))

    # Remove dir if no files left
    if len([name for name in os.listdir(os.path.join(OUTPUT_DIRECTORY, "content", dir)) if os.path.isfile(os.path.join(OUTPUT_DIRECTORY, "content", dir, name))]) == 0:
        os.rmdir(os.path.join(OUTPUT_DIRECTORY, "content", dir))

# Copy resources

shutil.copytree("resources", os.path.join(OUTPUT_DIRECTORY, "resources"))

shutil.copy("resources/favicon.ico", os.path.join(OUTPUT_DIRECTORY, "favicon.ico"))
os.unlink(os.path.join(OUTPUT_DIRECTORY, "resources", "favicon.ico"))

# Copy index page

with open(os.path.join(OUTPUT_DIRECTORY, "index.html"), "w") as f:
    f.write(main.index())

# Iter CTFs

writeups = main.load_writeups()

for ctf in writeups:
    os.makedirs(os.path.join(OUTPUT_DIRECTORY, ctf))

    # Copy CTF pages

    with open(os.path.join(OUTPUT_DIRECTORY, ctf, "index.html"), "w") as f:
        f.write(main.ctf(ctf))

    # Iter writeups

    for writeup in writeups[ctf]["writeups"]:
        os.makedirs(os.path.join(OUTPUT_DIRECTORY, ctf, writeup))

        with open(os.path.join(OUTPUT_DIRECTORY, ctf, writeup, "index.html"), "w", errors="ignore") as f:
            f.write(main.chall(ctf, writeup))
