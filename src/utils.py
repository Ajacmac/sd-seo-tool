import re


def extract_json_from_string(text):
    """Finds json in triple backtick string and returns it

    The primary purpose is to get valid json contained within an LM response,
    usually needed because they decided to say "Oh, I'd love to provide you
    with a json response. Here you go!" before outputting the actual json.

    Maybe I should make this more flexible, but lm's tend to just use triple backticks
    """
    match = re.search(r"(.*?)```([\s\S]*?)```(.*)", text, re.DOTALL)
    if match:
        before = match.group(1).strip()
        json_content = match.group(2).strip()
        after = match.group(3).strip()
        commentary = f"{before} {{{{json went here}}}} {after}"
        return {"commentary": commentary, "json": json_content}
    return {"commentary": text.strip(), "json": None}
