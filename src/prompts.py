# build sectionizer prompt for LLM
def build_sectionizer_prompt(resume_with_line_numbers: str) -> str:
    return (
        "You are a resume section parser. Your task is to analyze a resume provided as "
        "numbered lines and return a strict JSON object describing sections and their line ranges.\n\n"
        "Rules:\n"
        "1) Use 1-based line numbers that exactly match the provided numbering.\n"
        "2) Detect common headings and variants (e.g., 'PROFESSIONAL SUMMARY', 'ABOUT ME' → SUMMARY; "
        "'TECHNOLOGIES', 'TOOLS' → SKILLS; 'WORK EXPERIENCE', 'EMPLOYMENT' → EXPERIENCE; "
        "'PERSONAL PROJECTS' → PROJECTS; 'EDUCATION'/'ACADEMICS' → EDUCATION).\n"
        "3) For each section, return start_line and end_line inclusive. Headings belong to their section.\n"
        "4) Include a 'confidence' score in [0,1] for each section.\n"
        "5) If you can identify repeated substructures (like individual experience entries), include them under 'subsections' with start/end lines and basic metadata if visible (company/title/date_range/location). Omit fields you cannot infer.\n"
        "6) Output ONLY JSON. No prose.\n\n"
        "JSON schema to follow exactly:\n"
        "{\n"
        "  \"sections\": [\n"
        "    {\n"
        "      \"name\": \"SUMMARY|SKILLS|EXPERIENCE|PROJECTS|EDUCATION|OTHER\",\n"
        "      \"heading_text\": \"<exact heading line text>\",\n"
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
                         sections_json: str | None = None) -> str:
    return (
        "You are a resume editor tasked with tailoring a resume (provided as numbered lines) "
        "to a specific job description. Return a STRICT JSON object with surgical edits by line number.\n\n"

        "Editing policy (STRICT, with bounded embellishment):\n"
        "- Edit ONLY when it materially improves alignment with the job description; otherwise leave lines unchanged.\n"
        "- Keep truthful content only; do NOT invent experience, ownership, employers, dates, or metrics.\n"
        "- Embellishment is allowed for tone/clarity/confidence IF grounded in existing resume facts:\n"
        "  • You may strengthen vague verbs to precise ones when the action is already evidenced (e.g., 'worked on' → 'implemented' only if the line shows building/ownership; otherwise use 'contributed to').\n"
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
        "2) For tiny tweaks, use 'replace_line'. For multi-line rewrites, use 'replace_range' only if necessary.\n"
        "3) To add a new bullet directly after a line, use 'insert_after' (only to split existing substance for clarity or to surface job-relevant detail already present elsewhere in the resume).\n"
        "4) To remove irrelevant content, use 'delete_range' and explain why it hurts alignment.\n"
        "5) Never output lines that don't exist; validate with 'current_snippet' to avoid drift.\n"
        "6) Keep proper tech casing (TypeScript, JavaScript, PostgreSQL) and only correct if wrong.\n\n"

        "Output ONLY JSON matching this schema exactly:\n"
        "{\n"
        "  \"version\": 1,\n"
        "  \"meta\": { \"strategy\": \"rule\", \"model\": \"<model_name>\", \"created_at\": \"<ISO8601_timestamp>\" },\n"
        "  \"ops\": [\n"
        "    { \"op\": \"replace_line\", \"line\": <int>, \"text\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"replace_range\", \"start\": <int>, \"end\": <int>, \"text\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"insert_after\", \"line\": <int>, \"text\": \"string\", \"why\": \"string (optional)\" },\n"
        "    { \"op\": \"delete_range\", \"start\": <int>, \"end\": <int>, \"why\": \"string (optional)\" }\n"
        "  ]\n"
        "}\n\n"

        "Requirements:\n"
        "- Include version: 1 and meta object with strategy, model, and ISO8601 timestamp\n"
        "- For 'why' field (optional): Name the job phrase this targets and why it improves alignment\n"
        "- For replace_range: 'text' should be multi-line content (use \\n for line breaks)\n"
        "- For insert_after: 'text' should be the content to insert (use \\n for multiple lines)\n"
        "- Use exact line numbers from the numbered resume provided\n\n"

        "Job Description:\n"
        f"{job_info}\n\n"
        + (f"Known Sections (JSON):\n{sections_json}\n\n" if sections_json else "") +
        "Resume (numbered lines start at 1):\n"
        f"{resume_with_line_numbers}\n"
    )

