import re

# Dictionary to map month abbreviations to full month names
MONTH_FULL_NAMES = {
    'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 
    'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 
    'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
}

# Regular expression patterns for matching month and year
MONTH_PATTERN = r'\b(Jan(?:uary)?|Feb(?:ruary|raury)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b'
YEAR_PATTERN = r'(\d{4})'

DOCUMENTS = 'src/testing_data'