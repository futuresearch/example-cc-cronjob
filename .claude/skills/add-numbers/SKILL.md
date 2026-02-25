---
name: add-numbers
description: A minimal example skill that adds two numbers, saves the result, and creates a PR.
---

# Add Numbers

Use the Python utility in `lib/add_numbers.py` to compute 2 + 3, then save the result and create a pull request.

## Steps

1. Run `python -m lib.add_numbers 2 3` and capture the JSON output.
2. Parse the result and write it to `output/result.txt` in the format:
   ```
   Run: <current date and time>
   Input: 2 + 3
   Result: 5
   ```
3. Create a new branch named `result/<date>`, commit the result file, push, and create a PR with the title "Add numbers result: <date>".
