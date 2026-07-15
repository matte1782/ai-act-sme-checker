# Gate 4 pre-mortem (ADR-011(2))

It is 3 months out and Gate 4 shipped a defect. Why?
1. Teaching-to-the-test: rules shaped to the 14 golden statuses, not the cited articles; the 15th real case gets a confident wrong verdict.
2. Precedence flipped (X4): a pre-applicability out-of-scope system reads NOT_APPLICABLE instead of INACTIVE, masking a future obligation.
3. HR_ANNEX_III derives NON_COMPLIANT from the use-case fact alone, telling an Annex III deployer 'violation' before Chapter III applies (2027-12-02).
4. A hand-typed applies_from drifts from corpus/timeline.yaml after the OJ refresh and no anchor test catches it.
5. X3 date selection fails open: an unknown 'when' fact silently picks the default deadline instead of UNDETERMINED.
