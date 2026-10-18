Earlier pure read-only bridge attempt failed at a production-count assertion before writing its intended bridge file. Tool-visible stderr was:

```text
Traceback (most recent call last):
  File "<stdin>", line 4, in <module>
AssertionError
```

This is a transcription of the original tool-visible output, not stderr redirected at that time; the first heredoc script was not saved as an original file. The exact prior selection expression is not preserved here, so its cause is not claimed. The corrected bridge selects the 133 production paths from the frozen 687 execution-input map and checks each c068 blob, 8f76 blob and current file byte-for-byte. This observer failure is not a product test failure or qualification. No product execution or repository write was performed.
