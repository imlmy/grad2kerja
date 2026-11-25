# Grad2Kerja

**An end-to-end AI platform that supports Malaysian fresh graduates from job discovery to interview readiness.**

Grad2Kerja brings three things that job seekers usually do on separate platforms into one place: finding suitable entry-level jobs, checking which skills they are missing, and practising interviews. It is built on a dataset of real Malaysian job postings from JobStreet, filtered to entry-level roles.

> Final Year Project, Bachelor of Software Engineering (Hons), University of Wollongong Malaysia.

## Features

- **Resume upload and parsing:** extracts skills, languages, education, experience and projects from a PDF resume.
- **AI job recommendation:** ranks entry-level jobs by semantic similarity between the resume and each job posting, with a match percentage.
- **Job browsing, search and filters:** search by job title and filter by location, industry and employment type.
- **Check Skill Match:** compares the resume's skills with a job's requirements and shows matched and missing skills, a match percentage and an AI-generated explanation.
- **AI mock interview:** five role-specific questions based on the job and the user's resume, answered by typing or voice, with a score and written feedback for each answer.
- **Interview history and feedback reports:** past sessions with overall scores and detailed reports.
- **Dashboard:** latest recommendations, skill match result and interview performance at a glance.

## How it works

| Module | Approach |
|---|---|
| Resume parsing | `pdfplumber` text extraction, then dictionary-based skill matching with spaCy `PhraseMatcher` against a skill dictionary built from the job postings |
| Job matching | `sentence-transformers` (`multi-qa-mpnet-base-cos-v1`) embeddings; cosine similarity between the resume and precomputed job embeddings; match % = round(cosine × 100) |
| Skill match | Set comparison of resume skills and job skills (soft skills and languages shown separately), with an explanation from the OpenAI API |
| Mock interview | Questions and answer evaluation by the OpenAI API (`gpt-4o-mini`); voice answers transcribed with Whisper (`whisper-1`) |

## Tech stack

- **Frontend:** Streamlit
- **Backend:** FastAPI
- **Database:** SQLite (user data only; job listings and embeddings are loaded into memory at startup)
- **AI / NLP:** Sentence-Transformers, spaCy, RapidFuzz, pdfplumber, OpenAI API
- **Data:** JobStreet job postings dataset (Mahadan, 2024) via Hugging Face

## Project structure

```
grad2kerja/
├── backend/        FastAPI app, database and request schemas
├── frontend/       Streamlit app and pages (views/)
├── modules/        Core logic: parsing, matching, skill match, interview, auth
├── notebooks/      Data preparation and embedding generation
├── scripts/        Test and check scripts
├── data/           Dataset, embeddings and app database (not in the repo, see below)
└── requirements.txt
```

## Getting started

### Prerequisites

- Python 3.11 or later
- An OpenAI API key (for skill match explanations, interview questions, answer evaluation and voice transcription)
- About 8 GB RAM

### 1. Clone and install

```bash
git clone https://github.com/imlmy/grad2kerja.git
cd grad2kerja
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Add your API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-api-key-here
```

### 3. Prepare the data

The dataset and embeddings are not stored in the repository because of their size. Generate them with the notebooks in `notebooks/`:

1. Run `01 data_preparation.ipynb` to download and filter the JobStreet dataset to entry-level jobs.
2. Run `notebooks/encode_mpnet_lean.py` to encode the job postings.
3. Run `02_embeddings.ipynb` to produce `data/jobs_entry_skills.csv` and `data/job_embeddings.npy`.

### 4. Run the app

Start the backend and the frontend in two terminals, both from the project root:

```bash
# Terminal 1: backend
uvicorn backend.main:app --reload

# Terminal 2: frontend
streamlit run frontend/app.py
```

Open the URL Streamlit prints (usually http://localhost:8501), register an account and upload a resume. A sample resume is provided in `data/sample_resume.pdf`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for questions, evaluation and explanations |
| `OPENAI_TRANSCRIBE_MODEL` | `whisper-1` | Model for voice transcription |
| `GRAD2KERJA_API` | `http://127.0.0.1:8000` | Backend URL used by the frontend |
| `GRAD2KERJA_DB` | `data/app.db` | SQLite database path |

## Testing

Scripts in `scripts/` check each module, for example:

```bash
python scripts/test_resume_parser.py
python scripts/test_matching.py
python scripts/test_backend.py     # uses a temporary database; makes real API calls
```

## Limitations

- Job listings come from a static dataset, not live job portals.
- The skill dictionary is fixed and may miss newer or very specialised skills.
- AI-generated questions and scores are practice guidance only and may vary between runs.

## Author

**Liew Mei Yan**, Bachelor of Software Engineering (Hons), Data Science specialisation, University of Wollongong Malaysia

Supervisor: Dr. Norsyela binti Muhammad Noor Mathivanan

## Acknowledgements

- Job postings dataset: Mahadan, M. A. (2024). *JobStreet job postings dataset* [Data set]. Hugging Face. https://huggingface.co/datasets/azrai99/job-dataset
