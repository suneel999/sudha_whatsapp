import unittest
from unittest.mock import patch, MagicMock
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

import app
from app import _handle_flow_completion

class TestFlowPersistence(unittest.TestCase):

    @patch('flow_handler.save_appointment')
    @patch('whatsapp_client.send_text_message')
    @patch('flow_handler.get_doctor_by_id')
    @patch('state_machine.get_session')
    @patch('state_machine.clear_session')
    @patch('state_machine.reset_to_main_menu')
    def test_end_to_end_flow_persistence(self, mock_reset, mock_clear, mock_get_sess, mock_get_doc, mock_send_msg, mock_save):
        # 1. Simulate data_exchange storing data
        mock_get_doc.return_value = {"id": "dr_rahul", "name": "Dr. Rahul", "specialty": "Orthopedics"}
        clinic = {"name": "Test Clinic", "phone": "123", "address": "Test Addr"}
        
        token = "test_token_999"
        test_data = {"doctor": "dr_rahul", "appointment_date": "2026-03-01", "time_slot": "10:00 AM"}
        test_payload = {"patient_name": "Persist Patient", "phone": "917981982040"}
        
        # This should store the data
        flow_handler.handle_data_exchange("DETAILS", test_data, test_payload, clinic)
        
        stored_data = flow_handler.get_flow_data(token)
        # Note: handle_data_exchange stores data if flow_token is provided in the call
        # But handle_flow_request is the one that extracts it. Let's call that.
        
        request_data = {
            "action": "data_exchange",
            "screen": "DETAILS",
            "data": test_data,
            "payload": test_payload,
            "flow_token": token
        }
        flow_handler.handle_flow_request(request_data, "default")
        
        stored_data = flow_handler.get_flow_data(token)
        self.assertEqual(stored_data["patient_name"], "Persist Patient")
        print(f"Data stored for token {token}")

        # 2. Simulate Webhook receiving nfm_reply (completion)
        mock_save.return_value = True
        
        # Trigger the handler in app.py directly to simulate the webhook result
        app._handle_flow_completion("917981982040", "test_phone_id", token)
        
        # Verify DB save was called with the stored data
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        self.assertEqual(kwargs['patient_name'], "Persist Patient")
        self.assertEqual(kwargs['doctor'], "Dr. Rahul (Orthopedics)")
        
        # Verify message sent
        mock_send_msg.assert_called_once()
        
        # Verify session reset and data cleared
        mock_reset.assert_called_once_with("917981982040")
        self.assertEqual(flow_handler.get_flow_data(token), {})
        print("Flow completion processed successfully, session reset, and data cleared.")

if __name__ == '__main__':
    unittest.main()
