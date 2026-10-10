# Authorship and AI assistance

## Author

**Eliandro P. Teles** — author and sole responsible party for this work.

No institutional affiliation is declared. The author holds a B.Eng. in Materials
Engineering; the tool and this document were produced independently, outside any
current appointment or enrolment, so no institution is named. Affiliation fields
on the citation metadata are deliberately absent rather than filled with a
relationship that does not exist.

## AI assistance — declared, not an author

The implementation, the verification runs, and the drafting of the paper were
carried out with the assistance of an AI coding agent (**Hermes Agent**, Nous
Research), used as a tool under the author's direction and verification.

**The assistant is not listed as an author.** Neither arXiv nor COPE nor ICMJE
permits AI authorship, and a fabricated author would be worse than none. This
declaration exists because undisclosed AI use is a live cause of retraction, not
as a courtesy.

This is disclosed plainly because it is already visible: commits in this
repository are attributed to the assistant. Hiding it in version control while
omitting it from the record would be the one inconsistent option.

### What the assistance consisted of

- Writing and refactoring the implementation.
- Running the analyses against the external datasets and reporting the numbers.
- Drafting and editing the prose of the paper.

### What it does **not** consist of

- The scientific judgments. Which value to trust, which discrepancy to keep
  rather than average, and whether a result was reportable were the author's
  calls.
- Verification of the numbers. Every claim in the paper is backed by a script in
  this repository that anyone can re-run, not by the assistant's assertion.

### One specific thing worth stating

Where the assistant's own hypothesis was the one the data refuted, this record
says so. Section 4, item 5 of the paper originally asserted that inverted signal
polarity corrupted the melting enthalpy by two orders of magnitude, and named a
figure (0.229 J/g). On re-measurement against a real trace **neither half
reproduced**: the polarity inference had selected a crystallisation event, and
the enthalpy was omitted rather than mis-scaled. The entry is struck through as
retracted, and the real defect found in that function is recorded separately
(§3.16).

A failure mode that specific-looking is one nobody re-checks. Recording that the
diagnosis was wrong, and why it survived, is evidence that the verification
worked — not an admission against it.
