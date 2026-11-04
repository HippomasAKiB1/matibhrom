# Jaeef's Data Collection Workspace

This folder is your staging workspace for collecting benchmark items across the 3 domains for **Matibhrom**.

## Files in this Directory

1. `legal_items.csv` — For Legal & Regulatory items (from `bdlaws.minlaw.gov.bd`).
2. `medical_items.csv` — For Medical & Public Health items (from IEDCR, DGHS, WHO).
3. `general_items.csv` — For General Factual items (from BBS, national portal, encyclopedia).

---

## Target Breakdown

| Domain | Target Count | Key Sources |
|---|---|---|
| **Legal** | 200 items | [bdlaws.minlaw.gov.bd](http://bdlaws.minlaw.gov.bd) (Penal Code, CrPC, Labor Act, RTI, NI Act) |
| **Medical** | 200 items | [iedcr.gov.bd](https://iedcr.gov.bd), [dghs.gov.bd](https://dghs.gov.bd), WHO Bangladesh |
| **General** | 200 items | [nsds.bbs.gov.bd](https://nsds.bbs.gov.bd), [bangladesh.gov.bd](https://bangladesh.gov.bd) |

---

## Allowed Field Values

- **`answer_type`**: `entity`, `numeric`, `citation`, `procedure`, `short explanation`
- **`risk_tag`**: `normal` or `high-stakes`
- **`evidence_language`**: `bn`
- **`notes`**: Use `group_key:<topic_or_act>` (e.g., `group_key:penal_code_theft`) so related questions remain grouped.
