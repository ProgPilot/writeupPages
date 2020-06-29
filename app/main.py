import json
import os
from datetime import datetime

import bcrypt
import flask
import jinja2
import jsonschema
from werkzeug.exceptions import HTTPException

import parsers
import siteSearch

os.chdir(os.path.dirname(os.path.realpath(__file__)))  # Move to script location
SETTINGS_FILE = "settings.json"

app = flask.Flask(__name__)

j_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True
)


CACHE = {
    "categories": [],
    "tags": []
}


def load_settings():
    with open(SETTINGS_FILE) as f:
        s = json.load(f)
    return s


def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=4)


SETTINGS = load_settings()


def url_root():
    return SETTINGS["urlRoot"] if "GENERATING_STATIC" in os.environ else flask.request. url_root


class DefaultArguments(dict):
    def __init__(self):
        super().__init__({
            "urlRoot": url_root(),
            "siteTitle": SETTINGS["siteTitle"],
            "copyrightName": SETTINGS["copyrightName"],
            "lastModified": datetime.fromtimestamp(SETTINGS["lastModifiedTime"]).strftime("%a, %d %B @ %I:%M%p")
                if "GENERATING_STATIC" not in os.environ else datetime.now().strftime("%a, %d %B @ %I:%M%p")
        })


class Breadcrumb(list):
    def __init__(self):
        super().__init__([("Home", url_root())])

    def add(self, name, url):
        super().append((name, url))


def sort_dict(d):
    # Sorts dict by key
    s = dict(sorted(d.items(), key=lambda x: x[0].lower()))
    return s


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


def refresh_cache():
    global CACHE
    writeups = load_writeups()

    # refresh category cache
    categories = []
    for ctf in writeups:
        for chall in writeups[ctf]["writeups"]:
            category = writeups[ctf]["writeups"][chall]["category"]
            if category not in categories:
                categories.append(category)
    CACHE["categories"] = sorted(categories)

    # refresh tag cache
    tags = []
    for ctf in writeups:
        for chall in writeups[ctf]["writeups"]:
            chall = writeups[ctf]["writeups"][chall]
            if "tags" in chall:
                for tag in chall["tags"]:
                    tags.append(tag)
    CACHE["tags"] = sorted(tags)


def render_template(template, vars: dict):
    return j_env.get_template(template).render(**DefaultArguments(), **vars)


def render_error(error_code: int, error_message):
    return render_template("error.html", {"errorCode": str(error_code), "errorMessage": error_message}), error_code


def constant_time_compare(a, b):
    # Used when comparing password hashes
    # See https://www.tdpain.net/bookstack/books/programming-theory/page/preventing-against-timing-attacks
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def raise_on_duplicate_keys(ordered_pairs):
    # Raises on duplicate keys, used in validate_config
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(k)
        else:
            d[k] = v
    return d


def validate_config(obj_str):
    try:
        obj = json.loads(obj_str, object_pairs_hook=raise_on_duplicate_keys)  # this method will happily deal with
        # duplicate keys by combining entries
    except json.decoder.JSONDecodeError:
        return False, "Invalid JSON"
    except ValueError:
        return False, "CTF IDs must be unique and challenge IDs must be unique to their parent CTF -" \
                      " there are two or more occurrences of a key"

    with open("resources/writeups.schema.json") as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=obj, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        return False, str(e)

    return True, ""


add_error_handler = True
if "FLASK_DEBUG" in os.environ:
    if os.environ["FLASK_DEBUG"] == "1":
        add_error_handler = False
        j_env.cache = None  # disable template cache

if add_error_handler:
    @app.errorhandler(Exception)
    def handle_other_error(e):
        code = 500
        if isinstance(e, HTTPException):
            code = e.code

        if code == 500:
            return server_error()
        else:
            return render_error(code, str(e).split(": ")[-1])


# Easter egg
@app.after_request
def add_header(resp):
    resp.headers["x-powered-by"] = "Tiny cute kittens"
    resp.headers["x-servernickname"] = "Michael"
    return resp


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


@app.route("/content/<dir>/<file>")
def load_content(dir=None, file=None):
    if dir == None or file == None:
        return not_found_error()
    elif file.split(".")[-1].lower() == "pdf":
        return flask.send_from_directory(os.path.join("content", dir), file)

    return not_found_error()


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

    template_include = {}

    if ctf not in writeups:
        flask.abort(404)

    if "release_time" in writeups[ctf]:
        if writeups[ctf]["release_time"] > datetime.now().timestamp():
            template_include["not_released"] = True
            template_include["release_time"] = datetime.fromtimestamp(writeups[ctf]["release_time"]).\
                strftime("%a, %d %B @ %I:%M%p")

    categories = {}

    ctf_writeups = writeups[ctf]["writeups"]
    for writeup in ctf_writeups:

        c = {**ctf_writeups[writeup], **{"short_name": writeup}}

        if ctf_writeups[writeup]["category"] not in categories:
            categories[ctf_writeups[writeup]["category"]] = [c]
        else:
            categories[ctf_writeups[writeup]["category"]].append(c)

    categories = sort_dict(categories)

    breadcrumb = Breadcrumb()
    breadcrumb.add(writeups[ctf]["name"], flask.Request.base_url)

    return render_template("ctf.html", {
        **template_include,
        "ctfData": writeups[ctf],
        "positionSuffix": {"1": "st", "2": "nd", "3": "rd"}.get(str(
            writeups[ctf]["position"])[-1] if "position" in writeups[ctf] else "0", "th"),
        "categories": categories,
        "breadcrumb": breadcrumb,
        "urlPath": f"{ctf}/"
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
        content = parsers.pdf(url_root() + "content/" + res)

    breadcrumb = Breadcrumb()
    breadcrumb.add(writeups[ctf]["name"], "../")
    breadcrumb.add(chall_data["name"], "")

    return render_template("chall.html", {
        "ctfName": writeups[ctf]["name"],
        "challData": chall_data,
        "challContent": content,
        "breadcrumb": breadcrumb,
        "urlPath": f"{ctf}/{chall}",
        **({"tags": chall_data["tags"]} if "tags" in chall_data else {})
    })


# Do not include in static site
@app.route("/search/")
def search():
    start_time = datetime.now().timestamp()

    writeups = load_writeups()

    template_include = {}

    kwarg_include = {}

    if CACHE["categories"] == []:
        refresh_cache()

    if "c" in flask.request.args:
        if flask.request.args["c"] != "none":
            template_include["selectedCategory"] = flask.request.args["c"]
            kwarg_include["category_filter"] = flask.request.args["c"]

    if "t" in flask.request.args:
        if flask.request.args["t"] != "none":
            template_include["selectedTag"] = flask.request.args["t"]
            kwarg_include["tag_filter"] = flask.request.args["t"]

    if "q" in flask.request.args:
        template_include["searchQuery"] = flask.request.args["q"]
        template_include["results"] = siteSearch.search(flask.request.args["q"], writeups, **kwarg_include)

    breadcrumb = Breadcrumb()
    breadcrumb.add("Search", "")

    template_include["processingTime"] = round(datetime.now().timestamp() - start_time, 8)

    return render_template("search.html", {
        **template_include,
        "breadcrumb": breadcrumb,
        "categories": CACHE["categories"],
        "tags": CACHE["tags"]
    })


@app.route("/modify/", methods=["GET", "POST"])
def modify():
    render_arguments = {}
    response_code = 200

    if flask.request.method == "POST":
        auth_code = flask.request.form["authcode"]
        new_content = flask.request.form["config"]
        current_content = load_writeups(plaintext=True)

        success = False
        for cred in SETTINGS["credentials"]:
            if constant_time_compare(bcrypt.hashpw(auth_code.encode(), cred[1].encode()), cred[0].encode()):
                success = True

        if not success:
            render_arguments["mode"] = "unauth"
            response_code = 403
        else:
            # backup current config
            config_backups_dir = "configBackups"
            if not os.path.exists(config_backups_dir):
                os.mkdir(config_backups_dir)

            if current_content != new_content:
                validation_ok, message = validate_config(new_content)
                if not validation_ok:
                    render_arguments["mode"] = "bad"
                    render_arguments["message"] = message.replace("\n", "<br>")
                    response_code = 400
                else:
                    open(os.path.join("configBackups", f"{int(datetime.now().timestamp())}.json.bak"), "w").write(current_content)
                    SETTINGS["lastModifiedTime"] = int(datetime.now().timestamp())
                    save_settings(SETTINGS)
                    # modify config
                    open(os.path.join("resources", "writeups.json"), "w").write(new_content)
                    refresh_cache()
                    render_arguments["mode"] = "ok"
            else:
                render_arguments["mode"] = "notmod"
    else:
        render_arguments["mode"] = "modify"

    render_arguments["breadcrumb"] = Breadcrumb()
    render_arguments["breadcrumb"].add("Modify", "")

    return render_template("modify.html", render_arguments), response_code
