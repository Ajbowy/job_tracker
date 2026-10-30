import os
import tempfile
import unittest

import job_tracker as jt


class JobTrackerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        tmp.close()
        self.path = tmp.name

    def tearDown(self):
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def test_ensure_and_load(self):
        # ensure CSV created and loads as empty list
        jt.ensure_csv(self.path)
        jobs = jt.load_jobs(self.path)
        self.assertEqual(jobs, [])

    def test_create_and_save(self):
        jt.ensure_csv(self.path)
        jobs = jt.load_jobs(self.path)
        job = jt.create_job_record(jobs, 'Acme', 'Engineer', '2025-10-27', 'applied', 'note')
        jt.save_jobs(self.path, jobs)
        loaded = jt.load_jobs(self.path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['company'], 'Acme')
        self.assertEqual(loaded[0]['id'], job['id'])

    def test_update_and_delete(self):
        jt.ensure_csv(self.path)
        jobs = jt.load_jobs(self.path)
        job = jt.create_job_record(jobs, 'ACME', 'Dev', '2025-10-27', 'applied', '')
        jt.save_jobs(self.path, jobs)
        jobs = jt.load_jobs(self.path)
        ok = jt.update_job_record(jobs, job['id'], status='interview', notes='note2')
        jt.save_jobs(self.path, jobs)
        jobs = jt.load_jobs(self.path)
        self.assertTrue(ok)
        self.assertEqual(jobs[0]['status'], 'interview')
        ok2 = jt.delete_job_record(jobs, job['id'])
        jt.save_jobs(self.path, jobs)
        jobs = jt.load_jobs(self.path)
        self.assertTrue(ok2)
        self.assertEqual(len(jobs), 0)

    def test_backup_csv(self):
        # create and save one job, then backup the csv
        jt.ensure_csv(self.path)
        jobs = jt.load_jobs(self.path)
        jt.create_job_record(jobs, 'BackupCo', 'Tester', '2025-10-27', 'applied', '')
        jt.save_jobs(self.path, jobs)
        dest = jt.backup_csv(self.path)
        self.assertTrue(os.path.exists(dest))
        # contents should match
        with open(self.path, 'r', encoding='utf-8') as a, open(dest, 'r', encoding='utf-8') as b:
            self.assertEqual(a.read(), b.read())
        # clean up
        try:
            os.unlink(dest)
        except Exception:
            pass

    def test_sort_by_date_and_stats(self):
        jt.ensure_csv(self.path)
        jobs = jt.load_jobs(self.path)
        jt.create_job_record(jobs, 'A', 'X', '2025-01-01', 'applied', '')
        jt.create_job_record(jobs, 'B', 'Y', '2025-03-01', 'interview', '')
        jt.create_job_record(jobs, 'A', 'Z', '2024-12-15', 'rejected', '')
        # sort ascending
        s = jt.sort_jobs_by_date(jobs, reverse=False)
        dates = [j['date_applied'] for j in s]
        self.assertEqual(dates, ['2024-12-15', '2025-01-01', '2025-03-01'])
        # stats
        stats = jt.summary_stats(jobs)
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['by_status'].get('applied', 0), 1)
        self.assertEqual(stats['by_status'].get('interview', 0), 1)
        self.assertEqual(stats['by_company'].get('A', 0), 2)

    def test_create_job_record_rejects_blank_required_fields(self):
        jobs = []
        with self.assertRaises(ValueError):
            jt.create_job_record(jobs, '   ', 'Engineer', '2025-10-27', 'applied', 'note')
        with self.assertRaises(ValueError):
            jt.create_job_record(jobs, 'Acme', '   ', '2025-10-27', 'applied', 'note')

    def test_ensure_csv_creates_missing_parent_directory(self):
        nested_dir = os.path.join(os.path.dirname(self.path), 'nested', 'jobs_data')
        nested_path = os.path.join(nested_dir, 'jobs.csv')
        jt.ensure_csv(nested_path)
        self.assertTrue(os.path.exists(nested_path))
        with open(nested_path, 'r', encoding='utf-8', newline='') as fh:
            self.assertIn('id,company,position,date_applied,status,notes', fh.read())


if __name__ == '__main__':
    unittest.main()
