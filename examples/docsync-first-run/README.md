# DocSync First-Run Fixture

<!-- docsync:object docs.readme.tax_total -->
## Demo Service

The service README says `tax_total` applies the configured tax rate to a
subtotal. If the implementation changes, DocSync should ask reviewers to update
this claim or attest that the README is still accurate.
<!-- docsync:object.end docs.readme.tax_total -->

## Try The Review Loop

From this fixture directory:

```bash
python -m docsync doctor
git init
git add .
git commit -m "base"
```

Then edit `src/service.py` inside the evidence region and run:

```bash
python -m docsync check --base HEAD
python -m docsync prompt --base HEAD
```
