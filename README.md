
Name:        Hemant Nishad
Roll No.:    P26AI0005
Department:  SAIDE
Institute:   IITJ


Classical AI Logical Reasoning System
=====================================

1. CONTENTS
-----------

submission/
  reasoning_agent.ipynb   Complete implementation (Python notebook).
  report.pdf              Project report.
  submission.csv          Predicted labels for the official test set.
                          Columns: id, predicted_label (True / False).
  README.txt              This file.


2. WHAT THE SYSTEM DOES
-----------------------

Given a knowledge base (context or premises) and a query (statement or
conclusion), the system decides whether the query is entailed. It returns
True or False.

No generative or learned model makes the decision. Every prediction comes
from one of these classical reasoning engines:

  - RuleTaker:    rule-based reasoner with forward chaining, closed-world
                  (CWA) or open-world (OWA) semantics chosen per record.
  - CounterBench: structural causal model with Pearl's abduction, action
                  and prediction steps.
  - FOLIO:        first-order logic parser, Herbrand grounding, Tseitin CNF
                  conversion and a step-bounded DPLL solver.
  - General NL:   template-based parser with forward and backward chaining
                  (used as a fallback when FOLIO annotations are missing).

Natural-language input is converted into logic with fixed regular
expression templates. The conversion is part of the system design; the
final decision always comes from the reasoning engine.


3. REQUIREMENTS
---------------

  - Python 3
  - pandas
  - datasets          (Hugging Face, for downloading the datasets)
  - huggingface_hub   (for the login cell)
  - Jupyter Notebook or JupyterLab to run the .ipynb file

Install with:

  pip install pandas datasets huggingface_hub jupyter

All other modules (json, re, heapq, difflib, itertools, functools,
collections, csv, time, os, shutil, pathlib, urllib) are in the Python
standard library.


4. DATASETS
-----------

The notebook expects six .jsonl files in a folder named Data/ placed next
to the notebook:

  ruletaker_train.jsonl        hitachi-nlp/ruletaker, split "train"
  ruletaker_test.jsonl         hitachi-nlp/ruletaker, split "test"
  ruletaker_ood_test.jsonl     jise/ruletaker, split "ood_test"
  counterbench_alpha.jsonl     CounterBench, data_balanced_alpha_V1.json
  FOLIO_train.jsonl            yale-nlp/FOLIO, split "train"
  FOLIO_validation.jsonl       yale-nlp/FOLIO, split "validation"

The download cells fetch these automatically. If a download fails, copy
the file into Data/ by hand. The "DATASET LOCATOR" cell also searches the
usual download folders and copies any file it finds into Data/.

Note: the cell that downloads ruletaker_ood_test.jsonl writes to a
Windows-specific path (C:\Users\hp\Downloads\Data). On other machines,
change that path or copy the file into Data/ manually.


5. HOW TO RUN
-------------

Step 1. Place reasoning_agent.ipynb and the Data/ folder in the same
        directory.

Step 2. Open the notebook and run the cells from top to bottom. Run the
        cell titled "DATASET LOCATOR" before the evaluation cell.

Step 3. For the official test run, set OFFICIAL_INPUT_NAME in the
        section "6.2 EVALUATE ALL DATASETS" to the name of the official
        test file, for example:

            OFFICIAL_INPUT_NAME = "official_test.jsonl"

        Copy that file into Data/ first. Re-run the evaluation section.
        Without this setting, submission.csv covers only the first
        dataset found (ruletaker_train.jsonl), not the test set.

Step 4. The "Accuracy by dataset family" and "Runtime Summary" printouts
        give the accuracy and total inference time.

Optional: the section that loads the OOD file and prints its wrong
predictions is a diagnostic. It does not change any output.


6. OUTPUT FILES
---------------

submission.csv
 One row per record in every dataset processed.
  Columns: dataset, id, predicted_label

Records that have no id field get a generated id in the form
<filename>_<line number>. This applies to the RuleTaker records.


7. ERROR HANDLING
-----------------

If a record cannot be processed, the system predicts False for it, counts
it as an error, and prints a sample of the error message. Invalid JSON
lines are skipped and counted as errors. The run always continues to the
end.


8. KNOWN LIMITATIONS
--------------------

These are described in section 5 of report.pdf:

  - Predictions are binary. FOLIO's "Uncertain" label is treated as not
    entailed.
  - The DPLL solver stops after 100 nodes and the quantifier domain is
    capped at three constants. Some true entailments may be missed.
  - The natural-language parser covers only the sentence patterns in its
    templates.
  - Observations of derived variables are not used in the causal model.
  - The A* search is implemented but is not called by the prediction path.


9. REPRODUCING THE REPORTED NUMBERS
-----------------------------------

The accuracy and timing figures in report.pdf come from a saved run of
the notebook. Re-running can change them if the code or the data files
change. Compare against the printed output of your own run.
