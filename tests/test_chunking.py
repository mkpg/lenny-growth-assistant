import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.chunking import chunk_text

def test_basic_chunking():
    text = "This is a short test."
    chunks = chunk_text(text, max_length=1500, overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == "This is a short test."

def test_mid_word_cut_avoidance():
    text = "This is a long sentence that we want to split nicely."
    chunks = chunk_text(text, max_length=15, overlap=5)
    
    assert "long" in chunks[0]
    joined = " ".join(chunks)
    assert "sentence" in joined or ("senten" not in joined)

def test_no_spaces():
    text = "A" * 100
    chunks = chunk_text(text, max_length=15, overlap=5)
    assert len(chunks[0]) == 15
    assert len(chunks) > 1

def test_empty_text():
    assert chunk_text("") == []

def test_preservation_of_all_text():
    text = "Word1 word2 word3 word4 word5 word6 word7 word8 word9."
    chunks = chunk_text(text, max_length=15, overlap=5)
    # Check that every single word is present in the chunks
    for i in range(1, 10):
        word = f"word{i}" if i > 1 else "Word1"
        found = any(word in chunk for chunk in chunks)
        assert found, f"{word} is missing from chunks!"
        
def test_overlap_near_boundaries():
    text = "aaa bbb ccc ddd eee"
    chunks = chunk_text(text, max_length=7, overlap=3)
    # 0123456
    # aaa bbb (7 chars) -> chunk1 = aaa bbb
    # overlap = 3 -> next chunk starts at end - 3 = index 4 ( bbb). Next word is bbb.
    assert "bbb" in chunks[0]
    assert "bbb" in chunks[1]

def test_max_length_strictly_enforced():
    text = "This is a very long string that has lots of words."
    chunks = chunk_text(text, max_length=10, overlap=3)
    for c in chunks:
        assert len(c) <= 10

if __name__ == "__main__":
    test_basic_chunking()
    test_mid_word_cut_avoidance()
    test_no_spaces()
    test_empty_text()
    test_preservation_of_all_text()
    test_overlap_near_boundaries()
    test_max_length_strictly_enforced()
    print("All tests passed.")
