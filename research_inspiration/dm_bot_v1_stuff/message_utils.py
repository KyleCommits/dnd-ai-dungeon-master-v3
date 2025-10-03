import re

def split_message(content: str, limit: int = 2000) -> list[str]:
    """Split a message into chunks that fit Discord's character limit"""
    if len(content) <= limit:
        return [content]
    
    chunks = []
    current_chunk = ""
    
    # Split on sentence endings or newlines where possible
    sentences = re.split(r'([.!?\n]+)', content)
    
    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
        if len(current_chunk) + len(sentence) <= limit:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks