import flask
import jinja2
import json
import base64

import parsers
import os
from werkzeug.exceptions import HTTPException


os.chdir(os.path.dirname(os.path.realpath(__file__)))  # Move to script location
SETTINGS_FILE = "settings.json"

app = flask.Flask(__name__)

j_env = jinja2.Environment(
    loader = jinja2.FileSystemLoader("templates"),
    autoescape = True
)

class DefaultArguments(dict):
    def __init__(self):
        super().__init__({
            "urlRoot": flask.request.url_root,
            "siteTitle": "ProgPilot writeups"
        })


class Breadcrumb(list):
    def __init__(self):
        super().__init__([("Home", flask.request.url_root)])

    def add(self, name, url):
        super().append((name, url))


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
    with open("resources/writeups.json") as f:
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


def render_template(template, vars:dict):
    return j_env.get_template(template).render(**DefaultArguments(), **vars)


def render_error(error_code:int, error_message):
    return render_template("error.html", {"errorCode": str(error_code), "errorMessage": error_message}), error_code


@app.errorhandler(Exception)
def handle_other_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return render_error(code, str(e).split(": ")[-1])


@app.errorhandler(404)
def not_found_error(_=""):
    return render_error(404,
                        "The requested resource was not found<br>Think this is a mistake? "
                        "Report this issue: "
                        f"<a href='mailto:tom@progpilot.com?subject=HTTP 404 at {flask.request.url}' "
                        f"target='_blank' rel='noopener'>tom@progpilot.com</a>")


@app.errorhandler(500)
def server_error(_=""):
    return render_error(500, "Internal server error - try again later<br>Been like this for a while? "
                               "Report this issue: "
                               f"<a href='mailto:tom@progpilot.com?subject=HTTP 500 at {flask.request.url}'"
                               " target='_blank' rel='noopener'>tom@progpilot.com</a>")


@app.route("/resources/<rn>")
def load_resource(rn=None):
    return flask.send_from_directory("resources", rn)


@app.route("/favicon.ico")
def load_favicon():
    return flask.send_from_directory("resources", "favicon.ico")


@app.route("/")
def index():
    writeups = load_writeups()

    return render_template("index.html", {
        "totalWriteups": count_writeups(writeups),
        "writeups": writeups,
        "breadcrumb": Breadcrumb()
    })


@app.route("/<ctf>/")
def ctf(ctf):
    writeups = load_writeups()

    if ctf not in writeups:
        flask.abort(404)

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

    return render_template("ctf.html", {
        "ctfData": writeups[ctf],
        "positionSuffix": {"1": "st", "2": "nd", "3": "rd"}.get(str(
            writeups[ctf]["position"])[-1] if "position" in writeups[ctf] else "0", "th"),
        "categories": categories,
        "breadcrumb": breadcrumb
    })


@app.route("/<ctf>/<chall>/")
def chall(ctf, chall):
    writeups = load_writeups()

    if ctf not in writeups:
        flask.abort(404)

    if chall not in writeups[ctf]["writeups"]:
        flask.abort(404)

    chall_data = writeups[ctf]["writeups"][chall]

    if "type" in chall_data:
        data_type = chall_data["type"]
        if data_type in parsers.valid_content_types:
            writeup_type = data_type
        else:
            writeup_type = "unknown"
    else:
        writeup_type = "unknown"

    res = chall_data["resource"]
    if writeup_type == "unknown":
        raise Exception(f"Unknown writeup type for {ctf}/{chall}")
    elif writeup_type == "youtube":
        content = parsers.youtube(res)
    elif writeup_type == "html":
        content = parsers.html(open("content/" + res, encoding="utf8", errors="ignore").read())
    elif writeup_type == "pdf":
        content = parsers.pdf(flask.request.url_root + "content/" + res)

    breadcrumb = Breadcrumb()
    breadcrumb.add(writeups[ctf]["name"], "../")
    breadcrumb.add(chall_data["name"], "")

    return render_template("chall.html", {
        "challData": chall_data,
        "challContent": content,
        "breadcrumb": breadcrumb
    })


@app.route("/modify/", methods=["GET", "POST"])
def modify():
    render_arguments = {}

    if flask.request.method == "POST":
        auth_code = flask.request.form["authcode"]
        new_content = flask.request.form["config"]

        success = False
        for cred in creds.modify:
            # if constant_time_compare(hashlib.sha512(auth_code.encode()).hexdigest(), cred):
            if constant_time_compare(bcrypt.hashpw(auth_code.encode(), cred[1]), cred[0]):
                success = True

        if not success:
            return populate_error(403, f"Unauthorised {return_js}")
            # return "Unauthorised <script>window.setTimeout(function(){window.history.back();}, 2000);</script>", 403

        # backup current config
        config_backups_dir = os.path.join(DIR, "configBackups")
        if not os.path.exists(config_backups_dir):
            os.mkdir(config_backups_dir)

        if current_content != new_content:
            validation_ok, message = validate_config(new_content)
            if not validation_ok:
                return populate_error(400, f"{message}{return_js}")

            open(os.path.join(DIR, "configBackups", f"{int(time.time())}.json.bak"), "w").write(current_content)

            # modify config
            open(os.path.join(DIR, "resources", "writeups.json"), "w").write(new_content)

            return populate_error(200, f"Success {redirect_js}")  # this? naaaah, this is an error. totally.
        else:
            return populate_error(200, f"Not modified {redirect_js}")
    else:
        render_arguments["mode"] = "modify"
        render_arguments["content"] = load_writeups(plaintext=True)

    render_arguments["breadcrumb"] = Breadcrumb()
    render_arguments["breadcrumb"].add("Modify", "")

    return render_template("modify.html", render_arguments)
