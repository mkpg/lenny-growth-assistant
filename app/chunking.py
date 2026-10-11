import re

def chunk_text(text: str, max_length: int = 1500, overlap: int = 200) -> list[str]:
    """
    Splits text into chunks of maximum `max_length` characters, with `overlap` characters.
    It attempts to break chunks at the nearest word or sentence boundary (space or newline)
    preceding the max_length limit to avoid slicing words in half.
    """
    if not text:
        return []

    if max_length <= overlap:
        raise ValueError("max_length must be strictly greater than overlap.")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + max_length

        if end >= text_length:
            chunks.append(text[start:])
            break

        # If the character exactly at or just after 'end' is a space, we don't need to backtrack much
        if end < text_length and text[end] in (' ', '\n'):
            pass # We are at a perfect boundary
        elif end - 1 < text_length and text[end-1] in (' ', '\n'):
            pass # Also a perfect boundary
        else:
            # Look for the last space or newline before the 'end' index
            search_window_start = max(start, end - min(200, max_length - overlap))
            window_text = text[search_window_start:end]
            
            last_space_idx = window_text.rfind(' ')
            last_newline_idx = window_text.rfind('\n')
            best_boundary = max(last_space_idx, last_newline_idx)

            if best_boundary != -1:
                end = search_window_start + best_boundary
        
        chunks.append(text[start:end].strip())

        # Determine the next start position
        old_start = start
        overlap_target = end - overlap
        
        # Ensure we always make forward progress (no infinite loops)
        if overlap_target <= old_start:
            overlap_target = old_start + 1

        # We also want the new start to begin at a word boundary if possible
        if overlap_target > 0 and overlap_target < end:
            # Seek forward to the next space or newline
            while overlap_target < end and text[overlap_target] not in (' ', '\n'):
                overlap_target += 1
            if overlap_target < end:
                # We found a boundary, skip the whitespace character itself
                start = overlap_target + 1
            else:
                # Fallback if no boundary is found within the overlap window
                start = end - overlap
                if start <= old_start:
                    start = old_start + 1
        else:
            start = overlap_target
            
    return chunks
