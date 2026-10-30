# Job Tracker

A lightweight Python command-line application for tracking job applications, interview progress, and follow-up notes.

## Overview

This project helps you manage your job search in a simple, local CSV-based workflow. Each application record stores:

- company name
- job title/position
- application date
- current status
- notes

The app is designed to be easy to run, easy to understand, and easy to keep in a Git repository for portfolio use.

## Features

- Add job applications with company, role, date, status, and notes
- List all applications or filter by status/search term
- Update application status and notes
- Delete jobs with confirmation
- Backup the CSV data to a file
- View summary statistics by status and company
- Store data in a local CSV file for simplicity and portability

## Project structure

```text
job_tracker/
├── job_tracker.py          # main application logic
├── jobs.csv               # application data file
├── tests/
│   └── test_job_tracker.py
├── README.md
├── requirements.txt
├── .gitignore
├── demo.ps1               # optional Windows demo script
└── output files from demo runs (optional)
```

## Installation

### 1) Clone the project

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd job_tracker
```

### 2) Create a virtual environment

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> This project uses the Python standard library for runtime functionality. The only dependency listed for development/testing is `pytest`.

## Usage

### Interactive mode

```bash
python job_tracker.py
```

This opens the menu-based tracker where you can:

1. Add a job
2. View jobs
3. Update status/notes
4. Delete a job
5. Exit

### Command-line examples

#### Add a job

```bash
python job_tracker.py add --company "Acme" --position "Software Engineer" --date 2025-10-27 --status applied --notes "Applied through the company website"
```

#### List jobs

```bash
python job_tracker.py list
python job_tracker.py list --status interview
python job_tracker.py list --query "engineer"
```

#### Update a job

```bash
python job_tracker.py update 1 --status interview --notes "Phone screen scheduled"
```

#### Delete a job

```bash
python job_tracker.py delete 1 --yes
```

#### Backup the data file

```bash
python job_tracker.py backup --out backup.csv
```

#### Show summary statistics

```bash
python job_tracker.py stats
```

## Environment and security

This project does not require a database or API key for normal local use, so no secret configuration is required to run the core CLI.

If you add integrations later (for example, a web app, API client, or database), create a local `.env` file in the project root. Do not commit it to Git. Use the sample file as a template:

```bash
copy .env.example .env
# or on macOS/Linux:
cp .env.example .env
```

Then edit `.env` with your own local values only. Keep it out of version control.

Example structure:

```env
APP_NAME=job-tracker
APP_ENV=development
API_KEY=replace_with_your_local_key
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
```

> In this project, the default local data file is [jobs.csv](jobs.csv), and it is intentionally kept as a normal project file so your local job records remain available.

## Data storage

By default, saved jobs are stored in `jobs.csv` in the project folder. You can also use a custom CSV file with:

```bash
python job_tracker.py --csv path/to/your_jobs.csv list
```

The CSV fields are:

```text
id,company,position,date_applied,status,notes
```

## Default statuses

```text
applied
interview
rejected
offer
withdrawn
```

## Validation and safety

The application includes:

- required field validation for company and position
- date validation in `YYYY-MM-DD` format
- safe CSV writes using a temporary file before replacement
- confirmation before deleting a record
- automatic creation of missing parent directories for custom CSV paths

## Running tests

```bash
python -m pytest -q
```

## Demo guidance

A simple Windows PowerShell demo is included in `demo.ps1` to walk through add/list/update/stats/backup/delete flow.

To capture a screenshot for your portfolio:

1. Open PowerShell in the project folder
2. Run `python job_tracker.py --help`
3. Run a few commands such as add/list/stats
4. Capture the terminal output and the generated CSV file view
5. Save the images in a `screenshots/` folder if you want to document the project visually

## Notes

- This project is intentionally simple and does not use a web framework or database.
- It is designed to be easy to understand and easy to showcase as a Python portfolio project.
- The existing `jobs.csv` file is preserved and should not be deleted unless you intentionally want to reset the app data.

## License

This project does not currently include a license file. Add one before publishing it publicly if you plan to share it on GitHub or as part of a portfolio.
