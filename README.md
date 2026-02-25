# Work Process Reflection Canvas

AI-assisted application for mapping your work objective, pain points, and gain outcomes in a structured, exportable canvas.

## Quick Start

1. Open a terminal and install dependencies:
   ```bash
   cd /Users/hwitzthum/AGY-Projects/value-proposition-canvas
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. (Optional) Configure API keys:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI key if you want AI-generated suggestions
   ```

3. Start backend (Terminal 1):
   ```bash
   cd /Users/hwitzthum/AGY-Projects/value-proposition-canvas
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

4. Start frontend (Terminal 2):
   ```bash
   cd /Users/hwitzthum/AGY-Projects/value-proposition-canvas
   source venv/bin/activate
   streamlit run ui/streamlit_app.py
   ```

5. Open `http://localhost:8501`.

## Features

- ✅ Guided 5-step workflow from objective definition to export
- 🎨 Multiple visual themes (`Light`, `Dark`, `Sepia`, `Ocean`)
- ♿ In-app accessibility controls:
  - High Contrast
  - Low Motion
  - Large Text
- 🧭 Sticky guidance rail with step checklists and coaching context
- ⚡ Power input flow:
  - Press `Enter` to add pain/gain items quickly
  - Inline edit (`✏️`) and delete (`🗑️`) item controls
  - On-demand validation buttons in job/pain/gain steps
- 🧩 Rich pain/gain cards with lightweight metadata chips
- ✅ Validation for quality and independence of pain/gain points
- 🤖 AI suggestions for job, pain, and gain improvements (optional API key)
- 💾 Session auto-save / restore support
- 📥 Word document export (`.docx`) on review step

## Requirements

- Python 3.9+
- OpenAI API key (optional, only needed for AI suggestion quality)

## Small Tutorial (First Run)

### 1. Choose your working mode
- Open the app and use the **Appearance** control at the top-right.
- Pick a theme and optional accessibility settings (High Contrast, Low Motion, Large Text).

### 2. Step 1: Define your job
- Write one clear objective in the job description field.
- Click **Validate Now** to check quality.
- Improve until validation is accepted, then continue.

### 3. Step 2: Add pain points
- Add specific obstacles and friction points.
- Target at least **7 independent pain points**.
- Use `Enter` to add quickly.
- Use `✏️` to edit any item inline instead of deleting/retyping.

### 4. Step 3: Add gain points
- Add outcomes/benefits you want to achieve.
- Target at least **8 independent gain points**.
- Validate and refine until the step is accepted.

### 5. Step 4: Review and publish
- Review the publish-ready canvas.
- Go back and edit if needed.
- Download your Word file from **Download Your Canvas**.

## Keyboard Tips

- `Enter`: Add current pain/gain item in quick composer fields
- `Cmd/Ctrl + Enter`: Trigger step validation
- `Esc`: Cancel current inline edit

## Running the Application

Both backend and frontend must be running:

- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `streamlit run ui/streamlit_app.py`

Default UI URL: `http://localhost:8501`

## Project Structure

```text
value-proposition-canvas/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI backend
│   ├── coaching.py            # AI coaching engine
│   ├── validation.py          # Quality + independence validation
│   └── document_generator.py  # Word export
├── ui/
│   └── streamlit_app.py       # Streamlit frontend
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

- `GET /` - Health check
- `GET /api/config` - Configuration
- `POST /api/validate/job-description` - Validate job description
- `POST /api/validate/pain-points` - Validate pain points
- `POST /api/validate/gain-points` - Validate gain points
- `POST /api/suggestions` - Generate suggestions
- `POST /api/generate-document` - Generate Word document

## Troubleshooting

- If the frontend cannot reach the API, verify backend is running on `http://localhost:8000`.
- If port `8501` is busy, run Streamlit on another port:
  ```bash
  streamlit run ui/streamlit_app.py --server.port 8502
  ```
- If restore/save does not work, check file permissions in your home directory.

## License

MIT
