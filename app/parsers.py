valid_content_types = {
    "youtube",
    "html",
    "pdf"
}

def youtube(video_id):
    return "<div class='videoWrapper'><iframe width='100%' height='auto' " \
             "src='https://www.youtube.com/embed/{}' frameborder='0' allow='accelerometer; autoplay; " \
             "encrypted-media; gyroscope; picture-in-picture' allowfullscreen></iframe>" \
             "</div>".format(video_id)


def pdf(url):
    return "<iframe src='{}' style='width: 100%; height: 750px;'></iframe>".format(url)


def html(html):
    return html
