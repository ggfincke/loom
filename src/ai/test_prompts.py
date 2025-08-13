# src/ai/test_prompts.py
# Test prompts for purposeful fail cases to validate error handling and system robustness

# deliberately produces malformed JSON output
def build_invalid_json_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume parser. Parse the following resume and return JSON, "
        "but deliberately include syntax errors like unescaped quotes and newlines.\n\n"
        "Rules:\n"
        "1) Include unescaped quotes in string values\n"
        "2) Add literal newlines in JSON strings\n"
        "3) Missing commas between array elements\n"
        "4) Unclosed brackets\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates edits referencing non-existent line numbers
def build_out_of_bounds_edit_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate edits that reference line numbers "
        "that don't exist in the resume (e.g., line 999, negative lines).\n\n"
        "DELIBERATELY create these errors:\n"
        "- Reference line numbers higher than the resume length\n"
        "- Use negative line numbers\n"
        "- Create replace_range operations where start > end\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates multiple conflicting operations on the same lines
def build_conflicting_edits_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate multiple edit operations that conflict "
        "with each other on the same line numbers.\n\n"
        "DELIBERATELY create these conflicts:\n"
        "- Multiple replace_line operations on the same line\n"
        "- Overlapping replace_range operations\n"
        "- Insert and delete operations on the same line\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates replace_line operations with newline characters
def build_newline_in_replace_line_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate replace_line operations that contain "
        "newline characters (which should use replace_range instead).\n\n"
        "DELIBERATELY include:\n"
        "- Literal \\n characters in replace_line text\n"
        "- Multi-line text in single-line operations\n"
        "- Tab characters and other control characters\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates edit operations missing required fields
def build_missing_fields_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate edit operations that are missing "
        "required fields like 'op', 'line', 'text', etc.\n\n"
        "DELIBERATELY omit:\n"
        "- The 'op' field from operations\n"
        "- Line numbers from replace_line operations\n"
        "- Text content from edit operations\n"
        "- Start or end fields from replace_range operations\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates operations with invalid operation types
def build_invalid_operation_types_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate edit operations with invalid "
        "operation types that are not supported.\n\n"
        "DELIBERATELY use unsupported operations:\n"
        "- 'append_line' instead of 'insert_after'\n"
        "- 'modify_text' instead of 'replace_line'\n"
        "- 'remove_line' instead of 'delete_range'\n"
        "- Completely made-up operation names\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates edits with incorrect current_snippet values
def build_wrong_current_snippet_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate edit operations where the "
        "'current_snippet' field doesn't match the actual resume content.\n\n"
        "DELIBERATELY create mismatches:\n"
        "- current_snippet contains text that doesn't exist at the target line\n"
        "- current_snippet has different formatting/spacing\n"
        "- current_snippet references the wrong line entirely\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates edits that violate truthfulness constraints
def build_excessive_embellishment_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate edits that violate the truthfulness "
        "policy by inventing experience, metrics, and responsibilities.\n\n"
        "DELIBERATELY include:\n"
        "- Invented companies and job titles\n"
        "- Fabricated metrics and statistics\n"
        "- Added technical skills not present in original resume\n"
        "- Escalated scope beyond evidence (adding 'led', 'architected', etc.)\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates invalid section structure for sectionizer
def build_malformed_sections_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume parser. Parse sections but deliberately create "
        "invalid structure and data types.\n\n"
        "DELIBERATELY create errors:\n"
        "- start_line > end_line\n"
        "- Negative line numbers\n"
        "- Confidence scores outside [0,1] range\n"
        "- Missing required fields\n"
        "- Invalid section names\n"
        "- Overlapping section ranges\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# generates completely empty or null responses
def build_empty_response_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume parser. Return completely empty responses "
        "or responses that contain no useful data.\n\n"
        "DELIBERATELY return:\n"
        "- Empty JSON objects {}\n"
        "- Null values\n"
        "- Responses with no operations or sections\n"
        "- Plain text instead of JSON\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# wraps valid-looking JSON in code fences and extra prose
def build_code_fence_wrapped_json_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Return the edits JSON but wrap it in Markdown code fences "
        "and add a short explanation before it.\n\n"
        "Specifically do this:\n"
        "- Prepend a sentence of prose\n"
        "- Wrap JSON inside ```json ... ```\n"
        "- Append a closing sentence\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# uses JSON5 features (trailing commas, comments) that should be rejected by strict JSON parsers
def build_trailing_commas_and_comments_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume parser. Return an object that LOOKS like JSON but actually uses:\n"
        "- Trailing commas\n"
        "- // line comments and /* block comments */\n"
        "- Unquoted keys where possible\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# produces ops with 0-based (or mixed) line numbering
def build_zero_based_line_numbers_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Produce edits whose 'line', 'start', and 'end' values "
        "start at 0 instead of 1. Mix 0-based and 1-based where convenient.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# stringifies numeric fields (line/start/end as strings)
def build_stringified_numbers_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Produce edits where all numeric fields are strings, e.g. "
        '"line": "12", "start": "3", "end": "7".\n\n' 
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# emits Unicode control chars and invalid separators in string fields
def build_control_chars_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Intentionally include control characters in string values, such as:\n"
        "- U+0000 NULL, U+0001, U+0008\n"
        "- U+2028 (LINE SEPARATOR), U+2029 (PARAGRAPH SEPARATOR)\n"
        "Also mix in non-UTF-8 bytes if possible.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# massively oversized output to test max-ops and payload limits
def build_too_many_ops_prompt(job_info: str, resume_with_line_numbers: str, target_ops: int = 500) -> str:
    return (
        "You are a resume editor. Produce an extremely large number of tiny edits.\n"
        f"Create approximately {target_ops} operations that each touch a single line.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# randomly ordered ops (descending/unsorted) to test canonical ordering
def build_unsorted_ops_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Generate valid-looking edits but output them in random order, "
        "e.g., descending by line or shuffled.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# creates a chain of inserts that refer to lines introduced by prior inserts (potential loop/ambiguity)
def build_insert_after_chain_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Produce several insert_after operations where later operations refer to "
        "line numbers that only exist AFTER earlier inserts are applied (e.g., insert after last line, "
        "then insert after the newly created line, etc.).\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# drops required top-level fields (version/meta) or adds unexpected ones
def build_metadata_mismatch_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Output edits JSON with one or more of these issues:\n"
        "- Missing the 'version' field\n"
        "- Missing the 'meta' object\n"
        "- Extra unexpected top-level keys (e.g., 'notes', 'status')\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# uses wrong key casing / naming (camelCase instead of snake_case)
def build_wrong_key_casing_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Output the edits using camelCase keys instead of the specified snake_case ones, e.g., "
        "'currentSnippet', 'startLine', 'endLine'.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# valid JSON but wrapped in a top-level string or array instead of object
def build_wrong_top_level_type_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Return the edits as a top-level JSON string or array instead of an object.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# extremely long 'why' rationales to test length limits
def build_why_too_long_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Include a 'why' rationale for each op that is several hundred characters long.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )

# curly quotes / non-ASCII punctuation in JSON keys to break parsers
def build_smart_quotes_in_json_keys_prompt(job_info: str, resume_with_line_numbers: str) -> str:
    return (
        "You are a resume editor. Return JSON where the keys are quoted with “smart quotes” instead of standard quotes.\n\n"
        f"Job Description:\n{job_info}\n\n"
        f"Resume:\n{resume_with_line_numbers}\n"
    )