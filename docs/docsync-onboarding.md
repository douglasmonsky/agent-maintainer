<!-- docsync:object docs.docsync_onboarding.overview -->
# DocSync First-Run Tutorial

This tutorial is the first-run path for a repository that wants DocSync without
hand-writing the whole trace file. It starts with an empty `.docsync/` setup,
uses `docsync trace ...` commands to add reviewable claims, and ends with the
review packet a coding agent should read during a pull request.

## Starting Point

Assume the repository already has a short `README.md` and one implementation
file. The README makes a stable claim that should be reviewed whenever the
implementation evidence changes.

```text
README.md
src/service.py
```

## 1. Initialize DocSync

```bash
python -m docsync init
```

This creates `.docsync/config.yml`, `.docsync/trace.yml`, `.docsync/schema.json`,
`.docsync/attestations/`, and `.docsync/out/`. Use `python -m docsync init
--agents` only when the repository wants DocSync policy text added to
`AGENTS.md`.

## 2. Add Trace Entries

Create the document and object first:

```bash
python -m docsync trace add-document docs.readme \
  --path README.md \
  --title "Project README" \
  --audience users

python -m docsync trace add-object docs.readme.tax_total \
  --document docs.readme \
  --path README.md \
  --marker docs.readme.tax_total \
  --heading-level 1 \
  --heading-text "Project README" \
  --insert-marker
```

Then add evidence and the claim that depends on it:

```bash
python -m docsync trace add-evidence evidence.tax_total \
  --path src/service.py \
  --type code \
  --description "Tax total implementation" \
  --insert-region

python -m docsync trace add-claim claim.readme.tax_total \
  --object docs.readme.tax_total \
  --text "README explains the supported tax total behavior." \
  --severity high \
  --evidence evidence.tax_total
```

`--insert-marker` and `--insert-region` add starter comments. Move or fill the
evidence region so the changed implementation lines sit between
`docsync:evidence.start` and `docsync:evidence.end`.

## 3. Repair And Validate Structure

```bash
python -m docsync doctor --fix
python -m docsync doctor
```

`doctor --fix` is intentionally conservative. It creates missing starter
directories and inserts safe Markdown object end markers, then `doctor` verifies
the trace, document objects, evidence anchors, and required files.

## 4. Generate Review Signal

After committing the baseline, make an implementation change and compare the
working tree with that baseline:

```bash
python -m docsync check --base HEAD
python -m docsync prompt --base HEAD
```

`check` is the gate. `prompt` writes:

```text
.docsync/out/review-packet.json
.docsync/out/review-prompt.md
```

The packet should name the finding, claim ID, claim text, document object,
changed evidence snippet, linked document context, and suggested actions:
update the docs, update the claim, or run `docsync attest` when the documentation
was reviewed and remains accurate.

## Example Fixture

The fixture in `examples/docsync-first-run/` contains the same shape as this
tutorial: a README object, one evidence region, and a trace file linking a claim
to that evidence. It is small enough to copy into a scratch repository when
debugging DocSync onboarding.

## Acceptance Test

`tests/docsync/test_docsync_onboarding_flow.py` exercises the tutorial loop from
an empty `.docsync/` directory to an agent-readable review packet. If this
tutorial changes, update that acceptance test or the fixture in the same PR.
<!-- docsync:object.end docs.docsync_onboarding.overview -->
