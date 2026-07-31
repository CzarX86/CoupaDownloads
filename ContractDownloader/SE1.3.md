# PO Document Extraction & Excel Population Configuration

## Purpose
Automate extraction from vendor PO-related documents to populate Excel spreadsheets with automated quality checks and a single record-level confidence score.

Sheets produced:
- **Sheet 1:** Contract Tracker (always)
- **Sheet 2:** T&M Details (only for Time & Materials)
- **Sheet 3:** Milestone Details (only for Fixed Price)

---

## Scope
Process **PO-related contractual/commercial documents only**, including:
SOW, Change Request, Quotation, Order Form, Renewal Form, Invoice, or similar documents.

---

## Global Invariants
- Extract all required fields per record.
- Compute **one Confidence Score (0–100)** per record; **flag if <95**.
- Missing or ambiguous data → reduce score + flag + reason.
- **Do NOT request PO Number** from the user.
- Excel header styling (all sheets):
  - Background: `#F2CEEF`
  - Font: `#000000`
- If EUR and INR values are present, **capture INR values only**.
- Assign **L1/L2 classifications only from explicit allowed lists**.
- **Numeric-only guardrail** (else blank + confidence reduction + flag):
  - Total Value of PO
  - Discounts
  - Expenses
  - Total Cost in LC

---

## Contractual Commercial Type Guardrail
Assign **only one** type:
1. Explicit "Fixed Price" → Fixed Price
2. Explicit "Time & Materials / T&M" → T&M
3. Milestone-based billing mentioned → Fixed Price
4. Resource breakup present, no milestones, no fixed price → T&M

---

## Discount Extraction Guardrail
- Extract discounts **only if explicitly stated**.
- Require **discount rate AND both pre- & post‑discount totals**.
- Record **total monetary discount value only** (no %, no per-resource).
- If only a rate + single total is present → **leave Discounts blank**.

---

## Calculation Guardrails

### Total Cost in LC (T&M)
Must always be computed:

```
Count of Resources × Number of Man Days × Per Day Rate
```

 Never extract Total Cost in LC directly from the document.

### Unit Conversions
- Hours ÷ 8 → Man Days
- Months × 22 → Man Days
- Hourly Rate × 8 → Per Day Rate
- Monthly Rate ÷ 22 → Per Day Rate

---

# Sheet 1 — Contract Tracker (Always Populate)

**Field order (File Name must be FIRST):**
- File Name (uploaded file name)
- PO Number (user-supplied; else "Not Mentioned")
- Document Number
- Platform / Technology
- Contract Title (verbatim only; else "Not Mentioned")
- L2 Classification:
  - AD Services
  - AM Services
  - DevOps
  - Communication Services
  - PMO / Staff Aug / IT Consulting
  - IT Hardware
  - Infra / Hardware Maintenance
  - SaaS / Subscriptions / Licenses
- High Level Scope (2–3 lines)
- Contractual Commercial Type
- Contract Start Date
- Contract End Date
- Currency of PO
- Total Value of PO (numeric only)
- SOW FX (rate if present; else "Not Mentioned")
- TM Check: For Time & Material contracts only. Adapt the formula for the row number to correctly reference the PO Number. Populate the formula:
"=SUMIFS('T&M Tracker'!I:I,'T&M Tracker'!B:B,'Contract Tracker'!B2)".
- Confidence Score
- Flag (if <95)
- Flag Reason

---

# Sheet 2 — T&M Details (ONLY if T&M)

**Rules**
- **Each resource = one row. Never aggregate.**
- Carry forward **PO Number** and **File Name** from Sheet 1.
- File Name must be the **first field**.


**Fields**
- PO Number
- File Name
- Role (use person name if role not specified)
- Resource Country
- Count of Resources
- Number of Man Days (converted)
- Per Day Rate (converted)
- LC (currency; if missing → "Not Mentioned" + confidence reduction)
- Total Cost in LC (calculated only; numeric)
- Rate Card Type (explicit only; else "Rate Card Details Not Found")
- Rate Card Level (explicit only; else "Rate Card Details Not Found")
- Confidence Score
- Flag (if <95)

---

# Sheet 3 — Milestone Details (ONLY if Fixed Price)

**Rules**
- Each milestone = one row.
- If no milestones exist → create **one milestone equal to total document value**.
- Carry forward **PO Number** and **File Name** from Sheet 1 (File Name first).

**Fields**
- PO Number
- File Name
- Milestone Number (1, 2, 3…)
- Milestone Description (text only)
- Payment Information (percentage, amount, or terms)

---

## Numerical Guardrail (Strict)
If any numeric field contains **non-numeric characters**:
- Blank the field
- Reduce confidence
- Flag the record

---

## Workflow
1. Receive PO document(s).
2. Populate **Sheet 1 first**; compute confidence; apply header styling.
3. If T&M → populate **Sheet 2** with calculations and guardrails.
4. If Fixed Price → populate **Sheet 3** with milestone logic.
5. Update Excel, annotate low-confidence or guardrail failures, notify user.

---

## Error Handling
- Numeric violation → blank + confidence reduction + flag
- Critical info missing → confidence reduction + flag + alert
- Ambiguity → confidence reduction; flag if <95

---

## Feedback & Iteration
- Accept user corrections for flagged or low-confidence records.
- Reprocess and update Excel accordingly.

---

## Closure
Confirm completion and highlight records requiring manual review.