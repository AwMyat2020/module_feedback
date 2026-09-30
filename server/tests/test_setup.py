import os
import tempfile
import unittest
import secrets
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
from sample_data import seed
from database import connect
from auth import authenticate_account

class SampleSetupTests(unittest.TestCase):
    def test_fresh_seed_and_repeat_preserve_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'sample.sqlite3')
            password=secrets.token_urlsafe(24)
            with patch.dict(os.environ,{'MFI_DEMO_PASSWORD':password}): seed(path)
            user=authenticate_account(path,'login',dict(email='demo.staff@singaporetech.edu.sg',password=password))
            self.assertEqual(user['role'],'staff')
            with patch('sample_data.getpass.getpass',side_effect=AssertionError('Existing accounts must not prompt')): seed(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],4)
            self.assertEqual(authenticate_account(path,'login',dict(email='demo.staff@singaporetech.edu.sg',password=password))['userId'],user['userId'])
    def test_invalid_seed_password_does_not_insert_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'sample.sqlite3')
            with patch.dict(os.environ,{'MFI_DEMO_PASSWORD':'short'}), self.assertRaises(SystemExit): seed(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM modules').fetchone()[0],0)
