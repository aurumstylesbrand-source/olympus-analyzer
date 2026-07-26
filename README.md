# olympus-analyzer — THE CONSOLE + THE INTAKE (what this folder IS)

**Purpose:** (1) the Olympus Console app (olympus_console.html + server.js + analyze.js, deployed on Render) that
vets repos and generates project briefings; (2) the MAINTAINER's intake + memory: DUMPS/ (raw platform verdicts the
user drops), experience.md (the maintainer's canonical fix log), the API KEY file (tokens; never printed/committed).

**What belongs here:** console code + deploy files, DUMPS/ intake, experience.md, API KEY, .env, archive/ (old console versions).
**What does NOT belong here:** prompts/doctrine (-> ~/Desktop/olympus-workflow/), run/verdict corpora (-> ~/Desktop/olympus-agent-corpus/), accepted-project debriefs (-> ~/Desktop/olympus-experience/).

## The four folders of the system
| Folder | Purpose | Who reads it |
|---|---|---|
| ~/Downloads/olympus-analyzer | Console app + maintainer intake (DUMPS/) + maintainer log | Maintainer AI only |
| ~/Desktop/olympus-workflow | THE PROMPT SYSTEM — global doctrine project AIs read (+ sources/ = raw platform docs) | Project AIs + maintainer |
| ~/Desktop/olympus-agent-corpus | DATA — agent runs, auto-review verdicts, FP-panel reports, audit dumps (indexed) | Maintainer AI (studies -> distills into workflow) |
| ~/Desktop/olympus-experience | ACCEPTED debriefs + ALL_TIME_PRINCIPLES (the reviewer lens) | Project AIs via STARTUP protocol |
