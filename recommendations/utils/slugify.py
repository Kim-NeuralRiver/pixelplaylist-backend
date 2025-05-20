import re 
import unicodedata

# Normalise and slugify game titles for improved IGDB ITAD compatibility

def slugify_title(title: str) -> str:
    
    title = unicodedata.normalize('NFKD', title)  # Normalize Unicode characters
    title = title.encode('ascii', 'ignore').decode('ascii')  # Remove non-ASCII characters
    title = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "-", title)  # Replace spaces and hyphens with a single hyphen