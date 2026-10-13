import unittest
from unittest.mock import patch, MagicMock
import os
import json
import logging

# Set up logging to capture output
logging.basicConfig(level=logging.INFO)

# Mock environment variable
os.environ['WHATSAPP_PHONE_NUMBER_ID'] = 'test_id'

import flow_handler

class TestFlowBookingFix(unittest.TestCase):

    @patch('flow_handler.save_appointment')
    @patch('flow_handler.send_text_message')
    @patch('flow_handler._generate_booking_id')
    @patch('flow_handler.get_doctor_by_id')
    def test_handle_complete_success(self, mock_get_doc, mock_gen_id, mock_send_msg, mock_save):
        # Setup mocks
        mock_get_doc.return_value = {"id": "dr_mahesh", "name": "Dr. Mahesh Babu", "specialty": "Cardiology"}
        mock_gen_id.return_value = "APT_NEW_123"
        mock_save.return_value = True
        
        test_data = {"doctor": "dr_mahesh", "appointment_date": "2026-03-01", "time_slot": "10:00 AM"}
        test_payload = {"patient_name": "Test Patient", "phone": "919876543210"}
        clinic = {"name": "Mallika Hospitals", "phone": "12345", "address": "Mahabubnagar"}
        
        # Execute
        response = flow_handler.handle_complete(test_data, test_payload, "flow_token_123", clinic, "clinic_id")
        
        # Verify
        self.assertEqual(response["screen"], "SUMMARY")
        self.assertEqual(response["data"]["extension_message_response"]["params"]["booking_id"], "APT_NEW_123")
        
        # Verify single source of truth: ID generated once, saved, then sent
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        self.assertEqual(kwargs['booking_id'], "APT_NEW_123")
        
        mock_send_msg.assert_called_once()
        args, kwargs = mock_send_msg.call_args
        self.assertIn("APT_NEW_123", args[1])  # Message contains the correct ID
        self.assertEqual(args[0], "919876543210")

    @patch('flow_handler.save_appointment')
    @patch('flow_handler.send_text_message')
    def test_handle_complete_db_failure(self, mock_send_msg, mock_save):
        # Setup mocks
        mock_save.return_value = False # DB Fail
        
        test_data = {"doctor": "dr_mahesh", "appointment_date": "2026-03-01", "time_slot": "10:00 AM"}
        test_payload = {"patient_name": "Test Patient", "phone": "919876543210"}
        
        # Execute
        response = flow_handler.handle_complete(test_data, test_payload, "flow_token", {}, "cid")
        
        # Verify Fail Loudly
        self.assertIn("error", response["data"])
        self.assertEqual(response["data"]["error"], "Database reservation failed")
        mock_send_msg.assert_not_called()

if __name__ == '__main__':
    unittest.main()
