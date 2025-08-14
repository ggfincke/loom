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

### Better Comments Extension Tags
Uses selective semantic tagging for important information:

```python
# * Important function description (capitalize first letter after *)
def important_function():

# ! Deprecated method, do not use
def old_method():

# ? Should this method be exposed in the public API?
def questionable_method():

# todo refactor this method so that it conforms to the API
def needs_work():
```

**Usage Guidelines:**
- `*` (Green) - Only for important functions, not small helpers
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