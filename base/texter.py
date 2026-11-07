import re
import unicodedata


def normalize_text(text, include_raw=False, min_length=2):

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

    not_keywords = [
        'afin', 'ai', 'as', 'au', 'aussi', 'autre', 'autres', 'avec', 'avez', 'avoir',
        'avons', 'bien', 'car', 'ce', 'ceci', 'cela', 'celle', 'celles', 'celui', 'ces',
        'cet', 'cette', 'ceux', 'chez', 'dans', 'de', 'des', 'donc', 'dont', 'du',
        'elle', 'elles', 'en', 'es', 'est', 'et', 'ete', 'eux', 'fait', 'il',
        'ils', 'je', 'la', 'le', 'les', 'leur', 'leurs', 'lors', 'lui', 'ma',
        'mais', 'me', 'mes', 'meme', 'moins', 'mon', 'moi', 'même', 'ne', 'ni',
        'non', 'nos', 'nous', 'ont', 'on', 'ou', 'oui', 'par', 'pas', 'plus',
        'pour', 'que', 'qu', 'quoi', 'qui', 'sa', 'se', 'selon', 'ses', 'sommes',
        'son', 'sont', 'sous', 'suis', 'sur', 'ta', 'te', 'tes', 'toi', 'ton',
        'toujours', 'tous', 'tout', 'toute', 'toutes', 'tres', 'très', 'tu', 'un', 'une',
        'vers', 'vos', 'vous', 'y', 'été', 'êtes', 'être',

        'deux', 'profit', 'relevant',
    ]

    words = [w for w in words if w not in not_keywords and len(w) >= min_length]

    # Rejoin with single space
    text = ' '.join(words)

    if include_raw:
        text = f"{ text } { original }"

    return text