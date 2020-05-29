import flask
import jinja2
import json
import parsers
import os


os.chdir(os.path.dirname(os.path.realpath(__file__)))  # Move to script location
SETTINGS_FILE = "settings.json"

app = flask.Flask(__name__)

j_env = jinja2.Environment(
    loader = jinja2.FileSystemLoader("templates"),
    autoescape = True
)


class Breadcrumb(list):
    def __init__(self):
        super(Breadcrumb, self).__init__([("Home", "https://www.progpilot.com/writeups")])

    def add(self, name, url):
        super(Breadcrumb, self).append((name, url))


def sort_dict(d):
    # Sorts dict by key
    s = dict(sorted(d.items(), key=lambda x: x[0].lower()))
    return s


# Load settings
def load_settings():
    with open(SETTINGS_FILE) as f:
        s = json.load(f)
    return s


SETTINGS = load_settings()


def load_writeups(plaintext=False):
    with open("writeups.json") as f:
        if plaintext:
            return os.linesep.join([s for s in f.read().splitlines() if s])
        else:
            return sort_dict(json.load(f))


def count_writeups(wu_obj=None):
    if wu_obj == None:
        writeups = load_writeups()
    else:
        writeups = wu_obj
    count = 0
    for ctf in writeups:
        count += len(writeups[ctf]["writeups"])
    return count


@app.route("/")
def index():
    writeups = load_writeups()
    return j_env.get_template("index.html").render(
        totalWriteups = count_writeups(writeups),
        writeups = writeups,
        breadcrumb = Breadcrumb()
    )


@app.route("/<ctf>")
@app.route("/<ctf>/")
def ctf(ctf):
    writeups = load_writeups()

    if ctf not in writeups:
        return j_env.get_template("error.html").render(errorCode="404", errorMessage="CTF not found")

    categories = {}

    ctf_writeups = writeups[ctf]["writeups"]
    for writeup in ctf_writeups:
        c = {**ctf_writeups[writeup], **{"short_name":writeup}}
        if ctf_writeups[writeup]["category"] not in categories:
            categories[ctf_writeups[writeup]["category"]] = [c]
        else:
            categories[ctf_writeups[writeup]["category"]].append(c)

    categories = sort_dict(categories)

    breadcrumb = Breadcrumb()
    breadcrumb.add(writeups[ctf]["name"], flask.Request.base_url)

    return j_env.get_template("ctf.html").render(
        ctfData = writeups[ctf],
        positionSuffix = {"1": "st", "2": "nd", "3": "rd"}.get(str(
            writeups[ctf]["position"])[-1] if "position" in writeups[ctf] else "0", "th"),
        categories = categories,
        breadcrumb = breadcrumb
    )


if __name__ == "__main__":
    app.run()
