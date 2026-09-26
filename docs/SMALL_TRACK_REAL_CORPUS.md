# Real training corpus, 2026-09-26

The user superseded synthetic fine-tuning with real exam data. `data/small_track/` contains the twelve 2015–2026 main-session history papers and official keys downloaded directly from CKE. The 2023/2024 evaluated papers and 2015/2016 reserved holdouts are excluded from all new training.

`data/small_track_legacy/` adds downloaded paper and answer PDFs for 2007–2014 from the Arkusze.pl archive mirror. Every file has URL, SHA-256, bytes and extracted page text. These eight legacy pairs have NOT passed task/key alignment validation and are not used for training. In particular, 2007/2008 answer documents are annotated worked papers whose official authorship is not yet verified; 2009 contains both basic and extended keys. Do not describe this as twenty verified training-ready official key pairs. Twenty years of paper downloads are present, with twelve fully parsed pairs and six additional visibly CKE-authored key documents. Copyright remains CKE; no open redistribution license is asserted. Exam files remain ignored and are not uploaded to model recovery repositories.

`data/small_track_real_training/` initially contains 25 closed-text and 76 open-text official solution targets. Rubrics are never used as assistant answers. Empty solutions, extraction requiring PDF review, essay rubrics and obvious legal-footer contamination are excluded. Original paper/key hashes are retained in the manifest. Real image tasks receive actual offline Tesseract OCR separately, retaining original PNG hashes; Bielik remains a text model and OCR does not confer map or photograph understanding. The CPU worker only receives original training page images, never keys.

Four genuine essay exemplars supplement the main papers: one CKE Informator2015 example scoring12/12 and three Informator2025 examples scoring12/15,15/15,12/15. They are downloaded from https://bip.cke.gov.pl/attachments/download/8286 and https://bip.cke.gov.pl/attachments/download/10016. Source pages and hashes are embedded in each row. The latter guide was published2024 for2025; it is not the2024 evaluated paper. No generated essays were used. The Charlemagne15/15 example was excluded because its topic and three aspects overlap substantially with2024essay1. Broad historical-topic overlap naturally exists.

The real-only router `artifacts/small_track/router-real-2026-0926.json` uses candidate question/image/point features and weak rule labels from2017–2022/2025, with2026 reserved for weak-label validation. It is485357bytes and achieved87.18% agreement with those weak labels; this is not human-verified classification accuracy. SHA-256: f2a63e81376f1da0a7324323b997c972151a4f7e1af002c108b7a8fd53f66312. Prior synthetic-trained routers are historical and are not this candidate.

Final real image preprocessing completed152/152pages for181tasks; final286rows across routes25/43/76/138/4. All route file hashes, unique IDs, year exclusions and OCR provenance passed validation. No cloud worker remains active from this preprocessing.

Legacy extraction update:2010–2014 now have122parsedtasks,250points and matched keyIDs, with original pages rendered. Three papers2011–2013 pass structural page/key checks;2010task20 and2014task22 need original-page linkage repair. All five remain excluded from the frozen training snapshot pending content QA. Years2007–2009 remain unparsed. Thus17years have task extraction,12modernplus5legacy, not20training-readypapers.

## Optional legacy text expansion,2026-09-27

Twelve additional text-only rows have been staged separately in
`data/small_track_legacy_audit_20260927/optional-text-training.jsonl`:
two closed and ten open tasks, five from2012 and seven from2014.
SHA256: `39787692d5d6b8990d6f8f6a5bfa8b94dc0fc7bf377cc649f1eef6ad69db2122`.
Each target comprises exact selected positive official answer spans, with whitespace
normalization only; grading instructions and negative examples are excluded.
Questions are self-contained early-paper tasks, with archive watermarks/point-box
footers removed. Original source and candidate hashes are retained. Nothing was
appended to the frozen138-row corpus and no training was launched.

Authorship is corroborated by freshly downloaded primary examination-board keys:
[OKE Kraków2012](https://www.oke.krakow.pl/inf/filemgmt/visit.php?lid=3521),
SHA256 `300b46ab3b700354583d8212a76cd49e92d3b5b272b03a1c413bfa9168e22711`;
[OKE Poznań2014](https://www.oke.poznan.pl/files/cms/347/historia_pr_klucz.pdf),
SHA256 `0575c2b33f77c8d0dccfcae1b653f036470458b270091eb9a82783f1a45ba822`.
2010/2011/2013 rows were not added without independent primary-key corroboration.
The legacy parser's later shared-source sections can shift neighboring material
into the wrong task, while some answer fields contain rubric/negative-example
text. Thus122parsed rows do not mean122reliable additions. Images, ambiguous table
layouts and late source-dependent tasks remain excluded from this text expansion.
