import re, unicodedata


def normalize_text(text, include_raw=True, min_length=2):

    if not text: return ""

    original = text.lower()
    keep_as_space = str.maketrans({
        "'": " ", "°": " ", "’": " ", "′": " ", 
        ",": " ", ".": " ", "-": " ",
        "(": " ", ")": " ",
    })
    text = text.translate(keep_as_space)

    # Remove punctuation and extra whitespace
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    text = text.lower()
    
    # Remove accents (diacritics)
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    
    words = text.split()
    words = [word for word in words if len(word) >= min_length]

    # Rejoin with single space
    text = ' '.join(words)

    if include_raw:
        text = f"{ text } { original }"

    return text