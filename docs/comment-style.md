# Comment Formatting Style Guide

Based on analysis of `src/core/pipeline.py`

## Comment Types Used

### File Headers
```python
# src/path/filename.py
# Brief description using & instead of "and", & `w/` instead of "with"
```

### Function Comments
```python
# concise description of function purpose & parameters
def function_name():
```

### Test Case Comments
```python
# * Verify test fixtures are accessible & contain expected data
def test_fixtures_accessible(sample_resume_content, sample_job_description):
    assert "John Doe" in sample_resume_content
    assert "Software Engineer" in sample_resume_content
    assert "Python developer" in sample_job_description
    assert "Requirements:" in sample_job_description
```

### Better Comments Extension Tags
Uses selective semantic tagging for important information:

```python
# * Important function description (capitalize first letter after *)
def important_function():

# ! Deprecated method, do not use (we shouldn't have these anyways)
def old_method():

# ? Should this method be exposed in the public API?
def questionable_method():

# todo refactor this method so that it conforms to the API
# or todo for another feature/fix/expansion down the line
def needs_work():
```

**Usage Guidelines:**
- `*` (Green) - Important functions, not small helpers; also required for all test cases
- `!` (Red) - Deprecated/warning items
- `?` (Blue) - Design questions needing review  
- `todo` (Orange) - Actual refactoring tasks

### Section/Block Comments
```python
# describe what the following code block does
code_block()

# handle specific error conditions
error_handling()
```

### Operation Comments
```python
# replace single line
if op_type == "replace_line":

# delete lines
elif op_type == "delete_range":
```

### Logic Comments
```python
# sort ops by line number (descending) to avoid shifting issues
# move existing lines in descending order to avoid collisions
```

## Style Characteristics

- **Format**: Single-line comments only, no multi-line docstrings
- **Placement**: Always above the code being described
- **Tone**: Direct, imperative ("generate", "validate", "check")
- **Brevity**: Concise, assumes programmer familiarity
- **Punctuation**: Uses `&` instead of "and", `w/` instead of "with" minimal punctuation

## What's Present
- ✅ File headers with path and purpose
- ✅ Function-level descriptions
- ✅ Block-level operation comments
- ✅ Complex logic explanations
- ✅ Error handling context

## What's Absent
- ❌ Multi-line docstrings
- ❌ Parameter/return documentation
- ❌ Usage examples
- ❌ TODO/FIXME markers
- ❌ Performance notes