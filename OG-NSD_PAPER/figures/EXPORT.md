# Export του `pipeline_tikz.tex` για άλλο paper

Για να κάνεις export το σχήμα σε μορφές κατάλληλες για εισαγωγή σε άλλο paper:

```bash
bash scripts/export_pipeline_figure.sh
```

Το script παράγει:

- `figures/exports/pipeline.pdf` (vector, προτεινόμενο για LaTeX papers)
- `figures/exports/pipeline.svg` (vector, αν υπάρχει `pdf2svg` ή `dvisvgm`)
- `figures/exports/pipeline.png` (raster 300 DPI, αν υπάρχει ImageMagick)

Το script χρησιμοποιεί το standalone wrapper `figures/pipeline_tikz_standalone.tex`, το οποίο κάνει input το αρχικό `figures/pipeline_tikz.tex` χωρίς να αλλάζει το περιεχόμενο του σχήματος.
