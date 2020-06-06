import re
import jellyfish


RELEVANCE_THRESHOLD = 0.5


def _direct_compare(words:list, compare_to):
    """

    Removes non alphanumeric characters from inputs and compares them.
    If any combination of items is true, the function will return true.

    :param words: list of words to compare
    :param compare_to: string or list to compare to
    :return: boolean
    """
    words = [_remove_non_alphanumeric(w) for w in words]

    if type(compare_to) == list:
        compare_to = [_remove_non_alphanumeric(c) for c in compare_to]
        return any(w in c for w in words for c in compare_to)
    else:
        return any(w in _remove_non_alphanumeric(compare_to) for w in words)


def _similarity_compare(words:list, compare_to):
    if type(compare_to) != list:
        compare_to = [compare_to]

    points = 0
    running_total = 0

    for index, item in enumerate(compare_to):
        if len(item.split(" ")) > 1:
            compare_to.pop(index)
            [compare_to.append(c) for c in item.split(" ")]

    for c in compare_to:
        for w in words:
            score = jellyfish.jaro_winkler_similarity(w.lower(), c.lower())
            if score != 0.0:
                running_total += score
                points += 1

    if points != 0:
        running_total /= points

    return running_total


def _remove_non_alphanumeric(src):
    return re.compile('[\W_]+').sub("", src)


def search(search_items, wu_json:dict, no_ctf=False, category_filter=None, tag_filter=None):
    results = []
    search_items = search_items.lower()
    search_items = search_items.split(" ")


    if category_filter is not None or tag_filter is not None:
        no_ctf = True

    # Meta based search for writeups and CTFs
    # Searches only titles, short names, categories
    # Ranked via relevance
    for ctf in wu_json:

        # Compare CTF name
        ctf_name_similarity = _similarity_compare(search_items, wu_json[ctf]["name"])
        if not no_ctf:
            if ctf_name_similarity > RELEVANCE_THRESHOLD or search_items == [""]:
                results.append((wu_json[ctf]["name"], "ctf", [(ctf, wu_json[ctf]["name"])],
                                ctf_name_similarity))

        # Compare child writeups
        for writeup in wu_json[ctf]["writeups"]:

            writeup_info = wu_json[ctf]["writeups"][writeup]

            name_similarity = _similarity_compare(search_items, writeup_info["name"])
            category_similarity = _similarity_compare(search_items, writeup_info["category"])

            tag_similarity = 0

            if "tags" in writeup_info:
                num_tags = 0
                similarity = 0

                for tag in writeup_info["tags"]:
                    s = _similarity_compare(search_items, tag)
                    if s != 0.0:
                        similarity += s
                        num_tags += 1

                if num_tags != 0:
                    tag_similarity = similarity / num_tags


            if tag_similarity != 0:

                meta_similarity = (name_similarity * 0.5) + (tag_similarity * 0.5)

            else:
                meta_similarity = (name_similarity * 0.9) + (category_similarity * 0.1)

            to_be_appended = (writeup_info["name"], "writeup",
                              [(ctf, wu_json[ctf]["name"]), (writeup, wu_json[ctf]["writeups"][writeup]["name"])],
                              meta_similarity)

            if meta_similarity > RELEVANCE_THRESHOLD or search_items == [""]:
                ok_to_append = False

                if search_items == [""] and [category_filter, tag_filter] == [None, None]:
                    ok_to_append = True

                # This took an embarrasingly long time to get right
                if "tags" in writeup_info:
                    if tag_filter is not None and category_filter is not None:
                        if tag_filter in writeup_info["tags"] and category_filter == writeup_info["category"]:
                            ok_to_append = True
                    elif tag_filter is not None:
                        if tag_filter in writeup_info["tags"]:
                            ok_to_append = True
                    elif category_filter is not None:
                        if category_filter == writeup_info["category"]:
                            ok_to_append = True
                elif category_filter is not None and tag_filter is None:
                    if category_filter == writeup_info["category"]:
                        ok_to_append = True
                elif category_filter is None and tag_filter is None:
                    ok_to_append = True

                if ok_to_append:
                    results.append(to_be_appended)

    sorted_results = sorted(results, key = lambda i: i[-1], reverse=True)

    return sorted_results
