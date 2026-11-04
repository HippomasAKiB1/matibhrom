# Datasets

This directory contains the curated question-and-answer items and the source
catalogues used by the project. All CSV files are UTF-8 encoded and include
Bengali text alongside Banglish transliterations where applicable.

## Files

### General

- [`itemsGeneral.csv`](./itemsGeneral.csv) contains general Bangladesh-related
  questions and answers. Items cover topics such as the Constitution, national
  identity, geography, public institutions, history, and culture.
- [`sourcesGeneral.csv`](./sourcesGeneral.csv) contains the provenance records
  for general items. Each source is identified by a `source_id` such as
  `SRC_001`.

General item records use IDs beginning with `GEN_` and reference their source
through the `source_id` column.

### Medical

- [`itemsMedical.csv`](./itemsMedical.csv) contains Bangladesh-specific
  public-health and medical questions and answers, including immunization,
  mental health, tuberculosis, dengue, and related topics.
- [`sourcesMedical.csv`](./sourcesMedical.csv) contains the provenance records
  for medical items. Sources are primarily World Health Organization (WHO)
  Bangladesh or regional pages, identified by IDs such as `BDWHO_001`.

Medical item records use IDs beginning with `BDMED_`. They include a
`risk_tag` column; medical items are generally marked `high-stakes` and should
not be treated as personal medical advice.

## Item columns

The item CSVs share the following main fields:

- `collection_id`: unique item identifier.
- `author`, `collected_date`: collection metadata.
- `domain`, `subdomain`: subject classification.
- `question_bn`, `question_banglish`: Bengali and Banglish question forms.
- `gold_answer`, `answer_type`: expected answer and answer category.
- `reference_date`: date or time context when relevant.
- `evidence_full_text`, `evidence_language`: supporting evidence and its
  language.
- `source_id`: foreign-key-style link to the matching source catalogue.
- `risk_tag`, `notes`: safety and editorial metadata.

## Source columns

The source CSVs contain:

- `source_id`: unique identifier referenced by item records.
- `url`, `publisher`: source location and publisher.
- `published_date`, `accessed_date`: publication and retrieval metadata.
- `local_path`, `sha256`: optional local snapshot and integrity metadata.

## Data handling

Keep the `source_id` relationship intact when adding or modifying items.
Preserve the original source evidence and update `accessed_date` or snapshot
metadata when a source is refreshed. Medical content should be reviewed for
accuracy and currency before use in evaluation or downstream applications.
