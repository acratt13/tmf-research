import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
from tmf_research.processes import bounded_run
from tmf_research.providers import PublicWeb, ProviderError

class ProcessAndTransportTests(unittest.TestCase):
    def test_combined_stdout_stderr_limit_terminates_child(self):
        with self.assertRaises(ValueError):
            bounded_run([sys.executable,'-c','import os,time; os.write(2,b"x"*100000);time.sleep(30)'],max_output=1024,timeout=3)
    def test_wall_timeout_terminates_child(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            bounded_run([sys.executable,'-c','import time;time.sleep(30)'],timeout=.15)
    def test_bounded_input_and_both_output_streams(self):
        r=bounded_run([sys.executable,'-c','import sys;print(sys.stdin.read());print("diagnostic",file=sys.stderr)'],input='fixture',timeout=3)
        self.assertEqual(r.stdout.strip(),'fixture');self.assertEqual(r.stderr.strip(),'diagnostic')
    def test_dns_rebinding_revalidated_before_connection(self):
        public=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]
        private=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
        with patch('socket.getaddrinfo',side_effect=[public,private]),patch('socket.create_connection') as connect:
            with self.assertRaises(ProviderError):PublicWeb().fetch('https://example.com/')
            connect.assert_not_called()

if __name__=='__main__':unittest.main()
