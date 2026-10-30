import argparse
import csv
import os
import shutil
import sys
import tempfile
from datetime import date, datetime


CSV_HEADERS = ["id", "company", "position", "date_applied", "status", "notes"]
DEFAULT_STATUSES = ["applied", "interview", "rejected", "offer", "withdrawn"]


def normalize_status(value):
	"""Normalize a status string to lowercase and trim whitespace."""
	if value is None:
		return ""
	return str(value).strip().lower()


def normalize_required_text(value, field_name):
	"""Return a trimmed field value or raise ValueError if blank."""
	text = str(value).strip() if value is not None else ""
	if not text:
		raise ValueError(f"{field_name} is required.")
	return text


def csv_path(provided_path=None):
	if provided_path:
		return provided_path
	# place jobs.csv next to this script
	base = os.path.dirname(os.path.abspath(__file__))
	return os.path.join(base, "jobs.csv")


def ensure_csv(path):
	"""Ensure CSV exists and has headers."""
	if not path:
		raise ValueError("CSV path is required.")
	directory = os.path.dirname(os.path.abspath(path))
	if directory and not os.path.exists(directory):
		os.makedirs(directory, exist_ok=True)
	if not os.path.exists(path):
		with open(path, "w", newline='', encoding='utf-8') as f:
			writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
			writer.writeheader()


def load_jobs(path):
	ensure_csv(path)
	jobs = []
	with open(path, newline='', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for row in reader:
			if not row or not any((value or '').strip() for value in row.values()):
				continue
			normalized = {key: (row.get(key, '') or '').strip() for key in CSV_HEADERS}
			try:
				normalized['id'] = int(normalized.get('id', '')) if str(normalized.get('id', '')).strip() else None
			except (TypeError, ValueError):
				normalized['id'] = None
			jobs.append(normalized)
	return jobs


def save_jobs(path, jobs):
	ensure_csv(path)
	directory = os.path.dirname(os.path.abspath(path)) or '.'
	os.makedirs(directory, exist_ok=True)
	tmp_fd, tmp_path = tempfile.mkstemp(prefix='.jobs_', suffix='.csv', dir=directory)
	try:
		with os.fdopen(tmp_fd, "w", newline='', encoding='utf-8') as f:
			writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
			writer.writeheader()
			for job in jobs:
				out = {k: "" for k in CSV_HEADERS}
				for key in CSV_HEADERS:
					value = job.get(key, "")
					if value is None:
						out[key] = ""
					else:
						out[key] = str(value)
				out['id'] = str(out.get('id', '')).strip()
				writer.writerow(out)
		os.replace(tmp_path, path)
	except Exception:
		if os.path.exists(tmp_path):
			os.unlink(tmp_path)
		raise


def next_id(jobs):
	ids = [j['id'] for j in jobs if isinstance(j.get('id'), int)]
	return max(ids) + 1 if ids else 1


def create_job_record(jobs, company, position, date_applied=None, status='applied', notes=''):
	"""Create a job record and append to jobs (in-memory list). Returns the new job dict."""
	company = normalize_required_text(company, 'Company')
	position = normalize_required_text(position, 'Position')
	nid = next_id(jobs)
	if not date_applied:
		date_applied = date.today().isoformat()
	date_applied = validate_date_str(date_applied)
	job = {
		'id': nid,
		'company': company,
		'position': position,
		'date_applied': date_applied,
		'status': normalize_status(status) or 'applied',
		'notes': str(notes or '').strip(),
	}
	jobs.append(job)
	return job


def update_job_record(jobs, jid, status=None, notes=None):
	"""Update a job in the in-memory list by id. Returns True if updated."""
	for j in jobs:
		if j.get('id') == jid:
			if status is not None:
				j['status'] = normalize_status(status) or j.get('status', '')
			if notes is not None:
				j['notes'] = str(notes).strip()
			return True
	return False


def delete_job_record(jobs, jid):
	"""Delete job by id from the in-memory list. Returns True if deleted."""
	before = len(jobs)
	jobs[:] = [j for j in jobs if j.get('id') != jid]
	return len(jobs) != before


def add_job(path):
	jobs = load_jobs(path)
	try:
		company = normalize_required_text(input("Company name: "), "Company")
		position = normalize_required_text(input("Position/title: "), "Position")
		date_applied = input(f"Date applied (YYYY-MM-DD) [default {date.today().isoformat()}]: ").strip()
		if not date_applied:
			date_applied = date.today().isoformat()
		date_applied = validate_date_str(date_applied)
		print("Status options:", ", ".join(DEFAULT_STATUSES))
		status = normalize_status(input("Status [applied]: ")) or "applied"
		if status not in DEFAULT_STATUSES:
			print("Unknown status; saving as provided (you can standardize later).")
		notes = input("Notes (optional): ").strip()
		job = create_job_record(jobs, company, position, date_applied=date_applied, status=status, notes=notes)
		save_jobs(path, jobs)
		print(f"Added job id={job['id']} for {company} - {position}")
	except ValueError as exc:
		print(f"Error: {exc}")


def print_table(jobs):
	if not jobs:
		print("No jobs to show.")
		return
	# compute column widths
	cols = CSV_HEADERS
	widths = {c: len(c) for c in cols}
	for j in jobs:
		for c in cols:
			val = str(j.get(c, ""))
			widths[c] = max(widths[c], len(val))
	sep = " | "
	header = sep.join(c.ljust(widths[c]) for c in cols)
	print(header)
	print("-" * len(header))
	for j in jobs:
		row = sep.join(str(j.get(c, "")).ljust(widths[c]) for c in cols)
		print(row)


def view_jobs(path):
	jobs = load_jobs(path)
	if not jobs:
		print("No saved jobs.")
		return
	print("Options: [a]ll, [s]tatus filter, [q]uery by text")
	opt = input("View option [a]: ").strip().lower() or 'a'
	filtered = jobs
	if opt == 's':
		st = input("Status to filter by: ").strip().lower()
		filtered = [j for j in jobs if str(j.get('status','')).lower() == st]
	elif opt == 'q':
		q = input("Search term (company/position/notes): ").strip().lower()
		filtered = [j for j in jobs if q in str(j.get('company','')).lower() or q in str(j.get('position','')).lower() or q in str(j.get('notes','')).lower()]
	# sort by id
	filtered.sort(key=lambda x: x.get('id') or 0)
	print_table(filtered)


def find_job_by_id(jobs, jid):
	for j in jobs:
		if j.get('id') == jid:
			return j
	return None


def update_status(path):
	jobs = load_jobs(path)
	if not jobs:
		print("No jobs to update.")
		return
	try:
		jid = int(input("Job id to update: ").strip())
	except Exception:
		print("Invalid id")
		return
	job = find_job_by_id(jobs, jid)
	if not job:
		print("Job id not found")
		return
	print("Current:", job)
	print("Status options:", ", ".join(DEFAULT_STATUSES))
	new_status = input(f"New status [{job.get('status','')}]: ").strip().lower() or job.get('status','')
	if new_status and new_status not in DEFAULT_STATUSES:
		confirm = input(f"'{new_status}' is not a known status. Save anyway? (y/n) [n]: ").strip().lower() or 'n'
		if confirm != 'y':
			print("Aborting update.")
			return
	more_notes = input("Add/update notes (leave blank to keep): ").strip()
	# use programmatic updater
	update_job_record(jobs, jid, status=new_status, notes=more_notes if more_notes else None)
	save_jobs(path, jobs)
	print(f"Updated job id={jid}")


def delete_job(path):
	jobs = load_jobs(path)
	if not jobs:
		print("No jobs to delete.")
		return
	try:
		jid = int(input("Job id to delete: ").strip())
	except Exception:
		print("Invalid id")
		return
	job = find_job_by_id(jobs, jid)
	if not job:
		print("Job id not found")
		return
	print("About to delete:")
	print(job)
	confirm = input("Confirm delete? (y/n): ").strip().lower()
	if confirm != 'y':
		print("Delete cancelled.")
		return
	delete_job_record(jobs, jid)
	save_jobs(path, jobs)
	print(f"Deleted job id={jid}")


def show_menu():
	print("\nJob Tracker Menu")
	print("1) Add new job")
	print("2) View saved jobs")
	print("3) Update job status / notes")
	print("4) Delete job")
	print("5) Exit")


def main(argv):
	# interactive main kept for backwards compatibility
	p = None
	if len(argv) > 1:
		# if any args provided, hand off to argparse-based handler
		handle_cli_args(argv[1:])
		return
	path = csv_path(p)
	ensure_csv(path)
	while True:
		show_menu()
		choice = input("Choose an option: ").strip()
		if choice == '1':
			add_job(path)
		elif choice == '2':
			view_jobs(path)
		elif choice == '3':
			update_status(path)
		elif choice == '4':
			delete_job(path)
		elif choice == '5' or choice.lower() in ('q', 'quit', 'exit'):
			print("Goodbye")
			break
		else:
			print("Unknown option")


def validate_date_str(s):
	"""Validate a YYYY-MM-DD date string; return normalized ISO date or raise ValueError."""
	if not s:
		raise ValueError("empty date")
	try:
		dt = datetime.strptime(s, "%Y-%m-%d")
		return dt.date().isoformat()
	except ValueError:
		raise ValueError(f"Date '{s}' is not in YYYY-MM-DD format")


def backup_csv(src_path, out_path=None):
	"""Copy the CSV file to out_path. If out_path is None, create a timestamped backup in cwd and return its path."""
	if not os.path.exists(src_path):
		raise FileNotFoundError(f"Source CSV not found: {src_path}")
	if out_path:
		dest = out_path
	else:
		ts = datetime.now().strftime("%Y%m%d%H%M%S")
		base = os.path.basename(src_path)
		name = f"{os.path.splitext(base)[0]}_backup_{ts}.csv"
		dest = os.path.join(os.getcwd(), name)
	shutil.copy2(src_path, dest)
	return dest


def sort_jobs_by_date(jobs, reverse=False):
	"""Return a new list of jobs sorted by date_applied (ISO YYYY-MM-DD). Jobs without a valid date sort last."""
	def keyfn(j):
		v = j.get('date_applied', '')
		try:
			return datetime.strptime(v, "%Y-%m-%d")
		except Exception:
			return datetime.max
	return sorted(jobs, key=keyfn, reverse=reverse)


def summary_stats(jobs):
	"""Return summary stats: total count and counts per status and per company."""
	stats = {'total': 0, 'by_status': {}, 'by_company': {}}
	for j in jobs:
		stats['total'] += 1
		st = str(j.get('status','')).lower()
		stats['by_status'][st] = stats['by_status'].get(st, 0) + 1
		comp = str(j.get('company',''))
		stats['by_company'][comp] = stats['by_company'].get(comp, 0) + 1
	return stats


def handle_cli_args(args):
	parser = argparse.ArgumentParser(prog="job_tracker", description="Job application tracker")
	parser.add_argument("--csv", help="Path to CSV file (default: jobs.csv next to script)")
	sub = parser.add_subparsers(dest="cmd")

	# add
	addp = sub.add_parser("add", help="Add a new job")
	addp.add_argument("--company", required=True)
	addp.add_argument("--position", required=True)
	addp.add_argument("--date", help="Date applied YYYY-MM-DD")
	addp.add_argument("--status", default="applied")
	addp.add_argument("--notes", default="")

	# list
	listp = sub.add_parser("list", help="List saved jobs")
	listp.add_argument("--status", help="Filter by status")
	listp.add_argument("--query", help="Search term in company/position/notes")
	listp.add_argument("--format", choices=["table", "csv"], default="table", help="Output format; 'csv' copies the underlying CSV for backup")
	listp.add_argument("--out", help="Output path when using --format csv (default: jobs_backup_<timestamp>.csv)")
	listp.add_argument("--sort", choices=["id", "date"], default="id", help="Sort by column")
	listp.add_argument("--desc", action="store_true", help="Sort descending")

	# update
	up = sub.add_parser("update", help="Update a job's status/notes")
	up.add_argument("id", type=int)
	up.add_argument("--status")
	up.add_argument("--notes")

	# delete
	delp = sub.add_parser("delete", help="Delete a job by id")
	delp.add_argument("id", type=int)
	delp.add_argument("--yes", action="store_true", help="Don't prompt for confirmation")

	# backup (explicit)
	back = sub.add_parser("backup", help="Backup the CSV file")
	back.add_argument("--out", help="Output path for the backup file")

	# stats
	statp = sub.add_parser("stats", help="Show summary statistics")

	parsed = parser.parse_args(args)
	path = csv_path(parsed.csv) if getattr(parsed, 'csv', None) else csv_path(None)
	ensure_csv(path)
	if parsed.cmd == 'add':
		if parsed.status is not None:
			parsed.status = normalize_status(parsed.status)
		# validate date if provided
		if parsed.date:
			try:
				parsed.date = validate_date_str(parsed.date)
			except ValueError as e:
				print(e)
				return
		jobs = load_jobs(path)
		job = create_job_record(jobs, parsed.company, parsed.position, date_applied=parsed.date, status=parsed.status, notes=parsed.notes)
		save_jobs(path, jobs)
		print(f"Added job id={job['id']}")
	elif parsed.cmd == 'list':
		jobs = load_jobs(path)
		filtered = jobs
		if getattr(parsed, 'status', None):
			filtered = [j for j in filtered if str(j.get('status','')).lower() == str(parsed.status).lower()]
		if getattr(parsed, 'query', None):
			q = str(parsed.query).lower()
			filtered = [j for j in filtered if q in str(j.get('company','')).lower() or q in str(j.get('position','')).lower() or q in str(j.get('notes','')).lower()]
		# sorting
		if getattr(parsed, 'sort', 'id') == 'date':
			filtered = sort_jobs_by_date(filtered, reverse=getattr(parsed, 'desc', False))
		else:
			filtered.sort(key=lambda x: x.get('id') or 0, reverse=getattr(parsed, 'desc', False))
		if getattr(parsed, 'format', 'table') == 'csv':
			# perform a file copy backup of the underlying CSV
			out = getattr(parsed, 'out', None)
			try:
				d = backup_csv(path, out)
				print(f"CSV backed up to: {d}")
			except Exception as e:
				print(f"Backup failed: {e}")
		else:
			print_table(filtered)
	elif parsed.cmd == 'update':
		jobs = load_jobs(path)
		if parsed.status is not None:
			parsed.status = normalize_status(parsed.status)
		if parsed.status is not None and parsed.status not in DEFAULT_STATUSES:
			print(f"Warning: '{parsed.status}' is not a known status")
		ok = update_job_record(jobs, parsed.id, status=parsed.status if parsed.status is not None else None, notes=parsed.notes if parsed.notes is not None else None)
		if not ok:
			print("Job id not found")
			return
		save_jobs(path, jobs)
		print(f"Updated job id={parsed.id}")
	elif parsed.cmd == 'delete':
		jobs = load_jobs(path)
		job = find_job_by_id(jobs, parsed.id)
		if not job:
			print("Job id not found")
			return
		if not parsed.yes:
			print("About to delete:")
			print(job)
			confirm = input("Confirm delete? (y/n): ").strip().lower()
			if confirm != 'y':
				print("Delete cancelled.")
				return
		delete_job_record(jobs, parsed.id)
		save_jobs(path, jobs)
		print(f"Deleted job id={parsed.id}")
	elif parsed.cmd == 'backup':
		out = getattr(parsed, 'out', None)
		try:
			d = backup_csv(path, out)
			print(f"CSV backed up to: {d}")
		except Exception as e:
			print(f"Backup failed: {e}")
	elif parsed.cmd == 'stats':
		jobs = load_jobs(path)
		stats = summary_stats(jobs)
		print(f"Total jobs: {stats['total']}")
		print("By status:")
		for s, c in stats['by_status'].items():
			print(f"  {s}: {c}")
		print("By company (top 10):")
		for comp, c in sorted(stats['by_company'].items(), key=lambda x: -x[1])[:10]:
			print(f"  {comp}: {c}")
	else:
		parser.print_help()


if __name__ == '__main__':
	try:
		main(sys.argv)
	except KeyboardInterrupt:
		print("\nInterrupted. Goodbye.")
