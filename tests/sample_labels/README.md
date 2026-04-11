# Sample Nutrition Label Photos

Place 3-4 nutrition label photos here for OCR testing.

## How to use

1. Take clear photos of nutrition labels (good lighting, straight-on angle).
2. Save them here as `.jpg` or `.png`.
3. Run the raw OCR debug helper to see what Tesseract produces:

```bash
python -c "from tests.test_ocr import print_raw_ocr; print_raw_ocr('tests/sample_labels/YOUR_IMAGE.jpg')"
```

4. Use the raw output to verify and tune the regex patterns in `src/ocr/extractor.py`.

## Tips for good OCR results
- Shoot straight-on (avoid angles)
- Use good, even lighting (no shadows across the label)
- Keep the label fully in frame with some margin
- Higher resolution is better (at least 300 DPI equivalent)
