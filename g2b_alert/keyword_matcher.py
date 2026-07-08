import re


def normalize(text):
    text = str(text).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[-_/.,(){}\[\]:;]", "", text)
    return text.strip()


def parse_keywords(raw_text):
    raw_text = raw_text.replace("\n", ",")
    return [keyword.strip() for keyword in raw_text.split(",") if keyword.strip()]


def match_keywords(bid, keywords):
    search_text = f"{bid.title} {bid.agency} {bid.demand_agency}"
    normalized_search_text = normalize(search_text)
    return [keyword for keyword in keywords if normalize(keyword) in normalized_search_text]
