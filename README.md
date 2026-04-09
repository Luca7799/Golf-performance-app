# Golf Performance Analysis App

A local-first web app that analyses your Golfshot scorecard exports and gives you
personalised insights and practice recommendations.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

### 3. Upload your data

- Export your rounds from the Golfshot app as CSV
- Upload the file in the app
- Explore your metrics, trends, and recommendations

A sample file is included at `data/sample/example_golfshot.csv` to try immediately.

---

## Folder Structure

```
golf-performance-app/
├── app.py                        # Streamlit entry point
├── config/
│   └── column_mapping.yaml       # Column name mapping + thresholds
├── data/
│   └── sample/
│       └── example_golfshot.csv  # Example data file
├── src/
│   ├── data_ingestion/
│   │   └── loader.py             # CSV loading + column resolution
│   ├── data_cleaning/
│   │   └── cleaner.py            # Type casting, validation, round aggregation
│   ├── metrics/
│   │   └── calculator.py         # All metric formulas
│   ├── recommendations/
│   │   └── engine.py             # Rule-based recommendation engine
│   ├── insights/
│   │   └── analyzer.py           # Trends, consistency, narratives
│   └── ui/
│       └── components.py         # Reusable UI building blocks
├── requirements.txt
└── README.md
```

---

## Golfshot CSV Export — Expected Format

The app auto-detects column names. These are the expected fields:

| Field | Required | Example Values |
|---|---|---|
| Date | Yes | `2024-03-15`, `15/03/2024` |
| Course | Yes | `Pebble Beach` |
| Hole | Yes | `1` – `18` |
| Par | Yes | `3`, `4`, `5` |
| Score | Yes | `4`, `5`, `6` |
| Putts | No | `2`, `3` |
| Fairway Hit | No | `Yes`, `No`, `1`, `0` |
| GIR | No | `Yes`, `No`, `1`, `0` |
| Penalties | No | `0`, `1`, `2` |
| Distance | No | `350` (yards or metres) |
| Club | No | `Driver`, `7-iron` |

If your export uses different column names, add them to `config/column_mapping.yaml`.

---

## Adjusting Thresholds

Open `config/column_mapping.yaml` and edit the `thresholds:` section to adjust
when recommendations are triggered:

```yaml
thresholds:
  gir_poor: 40          # GIR % below this = weak approach (default: 40)
  putts_high: 36        # Putts/round above this = significant issue (default: 36)
  fairway_poor: 40      # Fairway % below this = inaccurate driving (default: 40)
  penalties_high: 2     # Penalties/round above this = poor risk management (default: 2)
```

---

## Deploying to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file to `app.py`
5. Deploy — no other configuration needed

The app is designed to be Streamlit Cloud-compatible with no local dependencies.

---

## Metrics Reference

| Metric | Formula |
|---|---|
| Average Score | Mean gross score per round |
| Score vs Par | Mean (total strokes − total par) per round |
| GIR % | Greens in regulation / total holes × 100 |
| Fairway % | Fairways hit / par 4+5 hole count × 100 |
| Putts per Round | Mean total putts per round |
| Penalties per Round | Mean total penalties per round |
