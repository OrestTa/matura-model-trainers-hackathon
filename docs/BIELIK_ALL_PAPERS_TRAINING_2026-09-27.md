# Bielik all-paper training dataset

User explicitly removed all year holdouts. Frozen `data/small_track_real_training_all_papers_v2` contains225 real supervised rows:38 closed text,11 closed image,127 open text,44 open image,5 official essay exemplars. No generated targets. Keys appear only as assistant training targets, never candidate input.

All36 non-essay canonical2023 questions are now training inputs, including original task-crop offlineOCR with verified image hashes. Any2023 score is training-set performance. The2023 essay has only a rubric and is not a target; five separate official worked exemplars supervise essay writing.

This is all available approved data, not all downloaded tasks. Twelve main-session papers2015–2026 supply parsed rows;12 independently reviewed2012/2014 legacy rows are added. Some official worked exemplars carry2013 publicationyear, which is not proof that2013 main-session paper was included. Downloaded2007–2011/2013 papers still have extraction or primarykey corroboration gaps. New2015/16/24 image rows without reviewed OCR boundaries are excluded explicitly; previous32 acceptedimage rows are retained. These are quality gaps, not heldouts.

Manifest records every rejected parsed row, source paper/key URLs and hashes, route file hashes and no excluded years. Compact summary: `artifacts/small_track/all-papers-training-v2-summary.json`. Frozen corpus includes225 rows, router449 candidate-only weak-label rows. Router training agreement is not independent accuracy.

Rebuild with `python3 scripts/small_track/prepare_all_papers_training.py` only when destination absent. Requires frozen clean-v3, downloaded parsed papers, canonical offlineOCR inputs and reviewed legacy inputs. No original frozen artifacts overwritten.
