from model.google_search_api import generate_combined_text
from model.getdataintoES import split_basic_words

def test_split_basic_words():
    input_string = "防脹氣奶瓶"
    expected_output = ["防脹氣奶瓶", "奶瓶", "氣奶", "脹氣", "防脹"]
    result = split_basic_words(input_string)
    assert set(result) == set(expected_output), f"Expected {expected_output} but got {result}"

    input_string = "安撫奶嘴"
    expected_output = ["安撫奶嘴", "奶嘴", "安撫", "撫奶"]
    result = split_basic_words(input_string)
    assert set(result) == set(expected_output), f"Expected {expected_output} but got {result}"

def test_generate_combined_text():
    snippet = "This is a snippet."
    htmlSnippet = "<p>This is an HTML snippet.</p>"
    og_description = "This is the Open Graph description using metatags."
    
    expected_output = "This is a snippet. <p>This is an HTML snippet.</p> This is the Open Graph description using metatags."
    result = generate_combined_text(snippet, htmlSnippet, og_description)
    
    assert result == expected_output, f"Expected {expected_output} but got {result}"