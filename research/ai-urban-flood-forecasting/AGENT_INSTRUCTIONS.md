# Instructions for document-analysis subagents

Workspace: /home/user/delft3dfm/research/ai-urban-flood-forecasting/
Read brief.md (checklist I1–I7) and sources.md first.

You process ONLY the source IDs assigned to you, ONE document at a time, completely, before the next.

For each document:
1. Structural scan: `pdfinfo`, `pdftotext -layout file.pdf -` and grep keywords (e.g. KI, neuronal, LSTM, CNN, Netz, Kanal, Pump, NSE, RMSE, Kalibrierung, Validierung, GPU, Training, Szenario, km, Einwohner, Haltung, Schacht, radar, accuracy, calibrat, verif). Form feed (\f) separates pages; compute PDF page numbers carefully (e.g. `pdftotext -f N -l N`). Also note printed page numbers if they differ.
   For slide decks / image-heavy pages, render pages to PNG (`pdftoppm -r 80 -f N -l N -png file.pdf /tmp/claude-0/.../scratchpad/<ID>_p`) into the scratchpad dir /tmp/claude-0/-home-user-delft3dfm/c18e9168-dce1-5fcf-a524-05edc09d509f/scratchpad and view them with the Read tool when text extraction misses figures/tables with numbers.
2. Read relevant parts in full context (paragraph before/after, table notes, conditions).
3. Write notes/S<ID>.md:
   - Top: document metadata (title, authors/organisation, date/version, project period, pages) and a structure map (sections → checklist IDs).
   - Then one entry per finding, in this exact format:

```
- **F01 | I3** — <finding paraphrased in English, with scope/units/conditions>.
  Locator: S0X | PDF p.N (printed p.M) | §x.y "Section title" | Table/Fig n
  Anchor: "<short verbatim phrase from the document, <15 words, copied EXACTLY in the original language>"
  Context: <conditions, caveats>
```
   - Record negative results explicitly for each checklist item not covered: "- **NEG | I7** — S0X does not report training hardware (searched: GPU, CPU, Rechner, Cluster, Cloud)."
   - For I4, explicitly mark each metric as one of: [CALIBRATION of physical/hydraulic model], [AI TRAINING/VALIDATION], [AI TEST/VERIFICATION on independent data/real events], or [UNCLEAR], and state why.
   - Be exhaustive for I1–I7: give every number (areas, lengths, counts of manholes/pipes/pumps, number of training scenarios, grid resolution, lead time, metric values, compute times, hardware).
4. Do NOT use knowledge from memory. Only what the document says.
5. Do not write draft.md (the coordinator does). When done, reply with a concise summary (≤400 words) of the key findings per checklist item, and the path(s) of the notes file(s).
