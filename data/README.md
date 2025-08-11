# Data Directory

This directory contains input files for the Loom resume tailoring tool.

## Expected Files

- **resume.docx** - Your resume document to be tailored
- **job.txt** - Job description text file for tailoring against

## Usage

Place your resume and job description files in this directory, then run:

```bash
loom sectionize  # Parse resume into sections
loom tailor      # Generate tailored resume edits
```

**Note**: Files in this directory (except this README) are ignored by git to keep personal documents private.