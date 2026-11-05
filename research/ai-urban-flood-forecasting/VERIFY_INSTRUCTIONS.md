# Instructions for verification subagents (stage 3)

Workspace: /home/user/delft3dfm/research/ai-urban-flood-forecasting/
You verify ONLY the claim IDs assigned to you in draft.md (claims are in Vietnamese; locators {Sxx: p.N, §..}; p.N = PDF page index).
Originals are in sources/ (see sources.md). notes/ are hints for where to look, NEVER evidence.

For EVERY assigned claim (no sampling):
1. Open the original at the cited PDF page directly: `pdftotext -layout -f N -l N sources/<file>.pdf -`. For slide decks / figures / numbers in images, render the page (`pdftoppm -r 80 -f N -l N -png <file> /tmp/claude-0/-home-user-delft3dfm/c18e9168-dce1-5fcf-a524-05edc09d509f/scratchpad/v_<ID>`) and view it with Read.
2. Read around it (whole paragraph/table, heading, conditions).
3. Compare fact, numbers, units, dates, scope qualifiers. For NEG claims ("không có ..."), search the WHOLE document for the relevant keywords before confirming.
   For [INF] claims, check the claims they rest on and whether the inference follows. Labels like [Calibration], [Verification AI], [Không rõ] are classifications — check that the classification is reasonable given the source.
4. Assign exactly one verdict: OK | WRONG | NOT-FOUND | BAD-REF | OUT-OF-CONTEXT | PARTIAL | STALE.
5. Write your results to verification_<group>.md as a markdown table:
| Claim | Source / locator checked | Verdict | What the source actually says (short paraphrase) | Action |
Write rows as you go.

Do NOT edit draft.md. Do not fix claims from memory; give hints in Action (e.g. correct page or value found in the source).
Final reply: "Checked N of N", counts per verdict, and a list of non-OK claims with a one-line reason and proposed correction (with exact locator).
