import re, unicodedata


def normalize_text(text):
    # print("in ----------------------------- "  + text)
    # Blank out special symbols
    keep_as_space = str.maketrans({
        "'": " ", "°": " ", "’": " ", "′": " ", 
        ",": " ", ".": " ", "-": " ",
        "(": " ", ")": " ",
    })
    text = text.translate(keep_as_space)

    # Remove punctuation and extra whitespace
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    text = text.lower()
    
    # Remove accents (diacritics)
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    
    words = text.split()
    words = [word for word in words if len(word) >= 3]

    # Rejoin with single space
    text = ' '.join(words)

    # print("out =========================== "  + text)
    return text