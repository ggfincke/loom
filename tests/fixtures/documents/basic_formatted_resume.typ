// loom-template: swe-typst
// Software Engineering Resume Template for Loom
// Self-contained, ATS-friendly format

// === Document Setup ===
#set document(title: "Resume", author: "John Doe")
#set page(margin: 1in, paper: "us-letter")
#set text(font: "New Computer Modern", size: 11pt)
#set par(justify: false, leading: 0.65em)

// === Helper Functions ===
#let name(content) = {
  align(center)[
    #text(size: 18pt, weight: "bold")[#content]
  ]
}

#let contact(..items) = {
  align(center)[
    #items.pos().join(" | ")
  ]
}

#let section-heading(title) = {
  v(0.5em)
  text(size: 12pt, weight: "bold")[#title]
  v(-0.3em)
  line(length: 100%, stroke: 0.5pt)
  v(0.3em)
}

#let entry(
  title: none,
  organization: none,
  location: none,
  dates: none,
) = {
  grid(
    columns: (1fr, auto),
    row-gutter: 0.3em,
    [*#title* #if organization != none [| #organization]],
    [#dates],
    [#if location != none [#emph[#location]]],
    [],
  )
}

// === Header ===
#name[John Doe]
#contact[Software Engineer][john.doe\@email.com][(555) 123-4567]

// === Professional Summary ===
= Professional Summary

Experienced software engineer with 5+ years developing web applications using modern frameworks and technologies.

// === Technical Skills ===
= Technical Skills

- *Programming Languages:* Python, JavaScript, TypeScript
- *Frameworks:* React, Django, FastAPI
- *Tools:* Git, Docker, AWS

// === Professional Experience ===
= Professional Experience

#entry(
  title: "Senior Software Engineer",
  organization: "Tech Corp",
  location: "San Francisco, CA",
  dates: "January 2021 - Present",
)
- Developed microservices architecture serving 500K+ users
- Led code reviews and mentored junior developers

#entry(
  title: "Software Engineer",
  organization: "StartupCo",
  location: "Remote",
  dates: "June 2019 - December 2020",
)
- Built full-stack web applications using React and Python
- Collaborated with product team on technical requirements

// === Education ===
= Education

#entry(
  title: "Bachelor of Science in Computer Science",
  organization: "State University",
  dates: "2019",
)
