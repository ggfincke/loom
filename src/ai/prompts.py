# src/ai/prompts.py
# Prompt templates for AI-powered resume sectionizing & tailoring operations

# build sectionizer prompt for LLM
def build_sectionizer_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume section parser. Your task is to analyze a resume provided as "
        "numbered lines and return a strict JSON object describing sections and their line ranges.\n\n"
        "Rules:\n"
        "1) Use 1-based line numbers that exactly match the provided numbering.\n"
        "2) Detect common headings and variants (e.g., 'PROFESSIONAL SUMMARY', 'ABOUT ME' -> SUMMARY; "
        "'TECHNOLOGIES', 'TOOLS' -> SKILLS; 'WORK EXPERIENCE', 'EMPLOYMENT' -> EXPERIENCE; "
        "'PERSONAL PROJECTS' -> PROJECTS; 'EDUCATION'/'ACADEMICS' -> EDUCATION).\n"
        "3) **LaTeX Section Detection**: Recognize these LaTeX section patterns as headings:\n"
        "   - Standard sections: \\section{Title}\n"
        "   - Starred sections: \\section*{Title}\n"
        "   - Custom commands: \\sectionhead{Title}, \\subsection{Title}, \\subsubsection{Title}\n"
        "   - Document structure: Ignore preamble commands (\\documentclass, \\usepackage, \\begin{document}) as these are setup, not content sections\n"
        "   - Extract the title text from within the curly braces as the heading_text\n"
        "4) For each section, return start_line and end_line inclusive. Headings belong to their section.\n"
        "5) Include a 'confidence' score in [0,1] for each section.\n"
        "6) If you can identify repeated substructures (like individual experience entries), include them under 'subsections' with start/end lines and basic metadata if visible (company/title/date_range/location). Omit fields you cannot infer.\n"
        "7) Output ONLY JSON. No prose.\n\n"
        "**LaTeX Context Notes**:\n"
        "- LaTeX resumes typically start with preamble (\\documentclass, \\usepackage, etc.) - treat as OTHER if needed\n"
        "- Section content appears between \\begin{document} and \\end{document}\n"
        "- Look for meaningful content sections, not structural/formatting commands\n"
        "- Custom commands like \\sectionhead{}, \\name{}, \\contact{} are section indicators\n\n"
        "JSON schema to follow exactly:\n"
        "{\n"
        "  \"sections\": [\n"
        "    {\n"
        "      \"name\": \"SUMMARY|SKILLS|EXPERIENCE|PROJECTS|EDUCATION|OTHER\",\n"
        "      \"heading_text\": \"<exact heading line text or LaTeX command>\",\n"
        "      \"start_line\": <int>,\n"
        "      \"end_line\": <int>,\n"
        "      \"confidence\": <float>,\n"
        "      \"subsections\": [\n"
        "        {\n"
        "          \"name\": \"EXPERIENCE_ITEM|PROJECT_ITEM|EDUCATION_ITEM\",\n"
        "          \"start_line\": <int>,\n"
        "          \"end_line\": <int>,\n"
        "          \"meta\": {\"company\"?: \"string\", \"title\"?: \"string\", \"date_range\"?: \"string\", \"location\"?: \"string\"}\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        "  \"normalized_order\": [\"...\"],\n"
        "  \"notes\": \"string\"\n"
        "}\n\n"
        "Resume (numbered lines start at 1):\n"
        f"{resume_with_line_numbers}\n"
    )

# build generate prompt for LLM
def build_generate_prompt(job_info: str,
                         resume_with_line_numbers: str,
                         model: str,
                         created_at: str,
                         sections_json: str | None = None) -> str:
    return (
        "You are a resume editor tasked with tailoring a resume (provided as numbered lines) "
        "to a specific job description. Return a STRICT JSON object with surgical edits by line number.\n\n"

        "Editing policy (STRICT, with bounded embellishment):\n"
        "- Edit ONLY when it materially improves alignment with the job description; otherwise leave lines unchanged.\n"
        "- Keep truthful content only; do NOT invent experience, ownership, employers, dates, or metrics.\n"
        "- Embellishment is allowed for tone/clarity/confidence IF grounded in existing resume facts:\n"
        "  • You may strengthen vague verbs to precise ones when the action is already evidenced (e.g., 'worked on' -> 'implemented' only if the line shows building/ownership; otherwise use 'contributed to').\n"
        "  • You may add non-numeric outcome phrases when fairly implied by the text (e.g., 'improved reliability/maintainability/clarity') but do NOT fabricate statistics or concrete numbers.\n"
        "  • You may reorder skills already present (e.g., foreground Java/Python) but must not introduce new tools not on the resume.\n"
        "  • Never escalate scope beyond evidence (no adding 'led/owned/architected/shipped to production' unless those words or equivalent claims already appear for that role).\n"
        "- Avoid juniorizing language (e.g., 'aspiring'); keep a confident, professional tone.\n"
        "- Maintain existing structure/format (single column, headings, bullets). Cosmetic changes only if they fix objective errors (spelling/grammar/tech casing like TypeScript/JavaScript/PostgreSQL) or clearly improve alignment.\n\n"

        "Job-signal alignment:\n"
        "- Extract the top 3–5 explicit skills/responsibilities from the job description first.\n"
        "- Tie each edit to at least one job phrase you’re targeting.\n"
        "- Prefer the smallest possible diff (word/phrase) over full rewrites.\n\n"

        "Safety checks BEFORE emitting an edit:\n"
        "1) 'current_snippet' MUST match the exact current line(s) verbatim; if not, SKIP that edit.\n"
        "2) Do not modify employer names, titles, dates, or locations unless there is a clear typo.\n"
        "3) Do not introduce metrics or concrete quantities that are not already present.\n"
        "4) If ownership/scope is unclear, hedge ('contributed to', 'supported') rather than escalate.\n\n"

        "Line-numbering rules:\n"
        "1) Use the exact 1-based line numbers provided.\n"
        "2) **CRITICAL VALIDATION RULE**: For 'replace_line', the text field must contain EXACTLY ONE LINE with NO \\n characters.\n"
        "   - WRONG: {\"op\": \"replace_line\", \"line\": 5, \"text\": \"Line 1\\nLine 2\"}\n"
        "   - RIGHT: {\"op\": \"replace_range\", \"start\": 5, \"end\": 6, \"text\": \"Line 1\\nLine 2\"}\n"
        "   - If your text contains \\n, you MUST use 'replace_range' instead.\n"
        "3) For tiny tweaks (single line), use 'replace_line'. For multi-line rewrites, use 'replace_range'.\n"
        "4) To add a new bullet directly after a line, use 'insert_after' (only to split existing substance for clarity or to surface job-relevant detail already present elsewhere in the resume).\n"
        "5) To remove irrelevant content, use 'delete_range' and explain why it hurts alignment.\n"
        "6) Never output lines that don't exist; validate with 'current_snippet' to avoid drift.\n"
        "7) Keep proper tech casing (TypeScript, JavaScript, PostgreSQL) and only correct if wrong.\n\n"

        "Output ONLY valid JSON matching this schema exactly. Ensure all string values are properly escaped:\n"
        "{\n"
        "  \"version\": 1,\n"
        f"  \"meta\": {{ \"strategy\": \"rule\", \"model\": \"{model}\", \"created_at\": \"{created_at}\" }},\n"
        "  \"ops\": [\n"
        "    { \"op\": \"replace_line\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"replace_range\", \"start\": <int>, \"end\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"insert_after\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"delete_range\", \"start\": <int>, \"end\": <int>, \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "  ]\n"
        "}\n"
        "**FINAL VALIDATION CHECKLIST** (validate before outputting):\n"
        "- No 'replace_line' operations with \\n characters in text field\n"
        "- All line numbers exist in the provided resume\n"
        "- No unescaped quotes, newlines, or control characters in JSON strings\n"
        "- All required fields present for each operation type\n\n"

        "Requirements:\n"
        f"- Include version: 1 and meta object with strategy, model ({model}), and timestamp ({created_at})\n"
        "- For 'current_snippet': Include the EXACT current text being modified (for validation)\n"
        "- For 'why' field (optional): Name the job phrase this targets and why it improves alignment. CRITICAL: Keep this field concise (under 100 chars) and avoid line breaks, tabs, or control characters that would break JSON parsing.\n"
        "- For replace_range: 'text' should be multi-line content (use \\n for line breaks)\n"
        "- For insert_after: 'text' should be the content to insert (use \\n for multiple lines)\n"
        "- Use exact line numbers from the numbered resume provided\n"
        "- IMPORTANT: All JSON string values must be properly escaped and contain no unescaped control characters (newlines, tabs, etc.)\n\n"

        "Job Description:\n"
        f"{job_info}\n\n"
        + (f"Known Sections (JSON):\n{sections_json}\n\n" if sections_json else "") +
        "Resume (numbered lines start at 1):\n"
        f"{resume_with_line_numbers}\n"
    )

# build edit prompt for fixing validation errors in edits.json
def build_edit_prompt(job_info: str,
                     resume_with_line_numbers: str, 
                     edits_json: str,
                     validation_errors: list[str],
                     model: str,
                     created_at: str,
                     sections_json: str | None = None) -> str:
    return (
        "You are a resume editor tasked with FIXING VALIDATION ERRORS in a previously generated "
        "edits JSON file. The edits were created to tailor a resume to a job description, but "
        "contain validation errors that prevent them from being applied.\n\n"

        "Your task is to CORRECT the existing edits to fix validation errors while preserving "
        "the original intent and improving job alignment. Do NOT generate entirely new edits.\n\n"

        "Common validation errors to fix:\n"
        "- 'replace_line text contains newline; use replace_range': Convert replace_line ops with "
        "  newlines to replace_range ops with proper start/end line numbers\n"
        "- 'line X not in resume bounds': Remove ops referencing non-existent lines\n"
        "- 'duplicate operation on line X': Remove or merge conflicting ops on same line\n"
        "- 'replace_range line count mismatch': Adjust text to match the range size or vice versa\n"
        "- Missing required fields: Add any missing 'op', 'line', 'text', 'start', 'end' fields\n"
        "- Invalid ranges: Fix start > end or negative line numbers\n\n"

        "Correction rules:\n"
        "1. FIX errors without changing the editing intent - preserve the original meaning\n"
        "2. For replace_line with newlines: Convert to replace_range with proper line boundaries\n"
        "3. For out-of-bounds lines: Either remove the op or adjust to valid line numbers\n"
        "4. For duplicate ops: Keep the most comprehensive edit or merge if possible\n"
        "5. For line count mismatches: Adjust the range to match the intended text length\n"
        "6. Maintain the same job-alignment improvements as the original edits\n"
        "7. Keep all valid operations unchanged\n\n"

        "Output ONLY valid JSON matching this schema exactly. Ensure all string values are properly escaped:\n"
        "{\n"
        "  \"version\": 1,\n"
        f"  \"meta\": {{ \"strategy\": \"edit_fix\", \"model\": \"{model}\", \"created_at\": \"{created_at}\" }},\n"
        "  \"ops\": [\n"
        "    { \"op\": \"replace_line\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"replace_range\", \"start\": <int>, \"end\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"insert_after\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"delete_range\", \"start\": <int>, \"end\": <int>, \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "  ]\n"
        "}\n"
        "CRITICAL: Validate your JSON before outputting. No unescaped quotes, newlines, or control characters allowed. Keep 'why' fields concise (under 100 chars).\n\n"

        "Validation Errors Found:\n"
        + "\n".join(f"- {error}" for error in validation_errors) + "\n\n"

        "Job Description:\n"
        f"{job_info}\n\n"
        + (f"Known Sections (JSON):\n{sections_json}\n\n" if sections_json else "") +
        "Resume (numbered lines start at 1):\n"
        f"{resume_with_line_numbers}\n\n"
        "INVALID Edits JSON (to be corrected):\n"
        f"{edits_json}\n"
    )

# build prompt operation prompt for user-driven content generation
def build_prompt_operation_prompt(user_instruction: str,
                                operation_type: str,
                                operation_context: str,
                                job_text: str,
                                resume_with_line_numbers: str,
                                model: str,
                                created_at: str,
                                sections_json: str | None = None) -> str:
    return (
        "You are helping tailor a resume to match a job description. A user has requested "
        "a specific modification to an edit operation through a custom instruction.\n\n"
        
        "Your task is to regenerate a single edit operation based on the user's instruction. "
        "The operation should align with the job requirements while following the user's "
        "specific guidance.\n\n"
        
        "Operation Details:\n"
        f"- Operation type: {operation_type}\n"
        f"- Context: {operation_context}\n\n"
        
        f"User Instruction: {user_instruction}\n\n"
        
        "Guidelines:\n"
        "- Generate content that directly fulfills the user's instruction\n"
        "- Maintain professional resume language and formatting\n"
        "- Align with job requirements where possible\n"
        "- Keep content truthful and grounded in existing resume context\n"
        "- Follow the same editing policy as the main generator (bounded embellishment only)\n"
        "- For 'replace_line': text must contain EXACTLY ONE LINE with NO \\n characters\n"
        "- For multi-line content: use 'replace_range' instead of 'replace_line'\n\n"
        
        "Output ONLY valid JSON matching this schema exactly. Ensure all string values are properly escaped:\n"
        "{\n"
        "  \"version\": 1,\n"
        f"  \"meta\": {{ \"strategy\": \"prompt_regeneration\", \"model\": \"{model}\", \"created_at\": \"{created_at}\" }},\n"
        "  \"ops\": [\n"
        "    { \"op\": \"replace_line\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "    // OR for multi-line content:\n"
        "    // { \"op\": \"replace_range\", \"start\": <int>, \"end\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "    // OR for insertions:\n"
        "    // { \"op\": \"insert_after\", \"line\": <int>, \"text\": \"string\", \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "    // OR for deletions:\n"
        "    // { \"op\": \"delete_range\", \"start\": <int>, \"end\": <int>, \"current_snippet\": \"string\", \"why\": \"string (optional)\" }\n"
        "  ]\n"
        "}\n\n"
        
        "**CRITICAL JSON VALIDATION**:\n"
        "- Include exactly ONE operation in the ops array\n"
        "- No unescaped quotes, newlines, or control characters in JSON strings\n"
        "- 'current_snippet' should contain the exact original text being modified\n"
        "- 'why' field should explain how this fulfills the user's instruction (under 100 chars)\n"
        "- Use exact line numbers from the numbered resume provided\n\n"
        
        "Job Description:\n"
        f"{job_text}\n\n"
        
        + (f"Resume Sections Context:\n{sections_json}\n\n" if sections_json else "") +
        
        "Full Resume (numbered lines for reference):\n"
        f"{resume_with_line_numbers}\n\n"
        
        "Generate a single JSON edit operation based on the user instruction:"
    )


