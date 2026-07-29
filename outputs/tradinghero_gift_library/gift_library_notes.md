# TradingHero Gift Library v1 Notes

## Outputs

- `gift_library.csv`: confirmed gift library v1. Currently contains only user-confirmed zero-budget inventory gifts.
- `zero_budget_gifts.csv`: zero-budget inventory gift subset.
- `gift_candidates_from_pdf.csv`: PDF-extracted candidate gifts for manual review.
- `gift_candidates_review_top.csv`: deduplicated review queue with priority, cleaned PDF price clues, and suggested category.
- `gift_library_v1_review.md`: readable review guide for confirmed zero-budget gifts and priority candidates.

## Extraction Scope

- PDFs parsed: 2
- Candidate gifts extracted: 369
- High-confidence candidates: 130
- Zero-budget candidates: 9
- Deduplicated review rows: 330
- Priority review rows: P1=18, P2=199

## Rules

- `gift_library.csv` is conservative and confirmed.
- PDF candidates are not automatically available gifts.
- `manual_status=待确认` rows should be reviewed before entering the official gift library.
- Zero-budget gifts have `actual_cost=0` and `budget_cost=0` because the user said these are inventory items.
- Price fields in candidate/review files are extracted from nearby PDF text, not live market prices.
- P0 means confirmed zero-budget inventory; P1 means review first; P2 means useful candidate; P3 means weak/noisy inspiration only.
