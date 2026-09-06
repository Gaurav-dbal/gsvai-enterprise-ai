"""
Automated Test Suite for NDR and System Notification Detection in GSVAI Enterprise AI.

Covers:
  Scenario A: Exchange NDR (Undeliverable: RE: ..., sender=MicrosoftExchange...@...)
              EXPECTED: system notification, no AI processing
  Scenario B: Postmaster-style NDR (sender=postmaster@..., mailer-daemon@...)
              EXPECTED: system notification, no AI processing
  Scenario C: Normal business email containing "delivery failed" in ordinary context
              EXPECTED: NOT classified as NDR, proceeds as business email
  Scenario D: Normal invoice email
              EXPECTED: routes to Invoice Agent
  Scenario E: Normal technical/general email
              EXPECTED: routes to appropriate agent (RAG or Data agent)
  Scenario F: EmailService deterministic bypass (Groq LLM is not called)
  Scenario G: EmailAutomationService trace generation and reply prevention safety guards
"""

import unittest
from unittest.mock import MagicMock, patch

from services.email_system_notification import (
    detect_system_notification,
    is_system_notification,
)
from services.agent_router_service import route_email, agent_router


class TestNDRSystemNotification(unittest.TestCase):
    """Unit and integration tests for NDR / System Notification filtering."""

    def test_scenario_a_exchange_ndr(self):
        """
        Scenario A: Exchange NDR
        subject = 'Undeliverable: RE: How to Create SR & Invoice'
        sender = 'MicrosoftExchange329e71ec88ae4615bbc36ab6ce41109e@GSVAIEnterpriseAI.onmicrosoft.com'
        EXPECTED: system notification, no AI processing
        """
        email = {
            "email_id": "TEST-A-001",
            "subject": "Undeliverable: RE: How to Create SR & Invoice",
            "sender_email": "MicrosoftExchange329e71ec88ae4615bbc36ab6ce41109e@GSVAIEnterpriseAI.onmicrosoft.com",
            "sender_name": "Microsoft Outlook",
            "body": (
                "Delivery has failed to these recipients or groups:\n\n"
                "user@externaldomain.com\n"
                "Your message couldn't be delivered. Despite repeated attempts to contact the recipient's email system...\n"
                "Diagnostic information for administrators:\n"
                "Remote Server returned '550 5.1.1 RESOLVER.ADR.RecipNotFound'"
            ),
        }

        # 1. Deterministic helper
        self.assertTrue(is_system_notification(email))
        detection = detect_system_notification(email)
        self.assertTrue(detection["is_system_notification"])
        self.assertEqual(detection["category"], "exchange_ndr")
        self.assertIn("Exchange", detection["reason"])

        # 2. Agent Router guard
        analysis = {
            "email_type": "system_notification",
            "priority": "low",
            "recommended_action": "ignore_system_notification",
        }
        routing = route_email(email, analysis)
        self.assertEqual(routing["agent"], "system_notification")
        self.assertEqual(routing["status"], "SYSTEM_NOTIFICATION")
        self.assertEqual(routing["action"], "ignore_system_notification")
        self.assertIsNone(routing["answer"])

    def test_scenario_b_postmaster_ndr(self):
        """
        Scenario B: Postmaster-style NDR
        sender = 'postmaster@mail.protection.outlook.com'
        EXPECTED: system notification
        """
        email = {
            "email_id": "TEST-B-001",
            "subject": "Delivery Status Notification (Failure)",
            "sender_email": "postmaster@mail.protection.outlook.com",
            "sender_name": "Postmaster",
            "body": "Action: failed\nStatus: 5.4.1\nDiagnostic-Code: smtp; 550 5.4.1 Recipient address rejected: Access denied",
        }

        self.assertTrue(is_system_notification(email))
        detection = detect_system_notification(email)
        self.assertTrue(detection["is_system_notification"])
        self.assertTrue(any("postmaster" in s.lower() for s in detection["signals"]))

        # Also test mailer-daemon variant
        mailer_daemon_email = {
            "email_id": "TEST-B-002",
            "subject": "Mail delivery failed: returning message to sender",
            "sender_email": "mailer-daemon@smtp.server.net",
            "body": "This message was created automatically by mail delivery software.",
        }
        self.assertTrue(is_system_notification(mailer_daemon_email))
        md_detection = detect_system_notification(mailer_daemon_email)
        self.assertTrue(md_detection["is_system_notification"])

    def test_scenario_c_business_email_with_delivery_words(self):
        """
        Scenario C: Normal business email containing 'delivery failed' in ordinary context
        EXPECTED: should NOT automatically be classified as NDR unless sufficient NDR signals exist.
        """
        email = {
            "email_id": "TEST-C-001",
            "subject": "Urgent: Delivery failed for warehouse shipment PO-99824",
            "sender_email": "logistics.manager@partner-logistics.com",
            "sender_name": "John Doe - Logistics",
            "body": (
                "Hi Gaurav,\n\n"
                "Our driver attempted delivery today to the Austin warehouse, but delivery failed "
                "because the loading dock was closed after 5pm.\n"
                "Can you please confirm the warehouse hours and schedule redelivery for tomorrow?\n\n"
                "Thanks,\nJohn"
            ),
        }

        self.assertFalse(is_system_notification(email))
        detection = detect_system_notification(email)
        self.assertFalse(detection["is_system_notification"])
        self.assertEqual(detection["category"], "business_email")

    def test_scenario_d_normal_invoice_email(self):
        """
        Scenario D: Normal invoice email
        EXPECTED: still reaches Invoice Agent normally.
        """
        email = {
            "email_id": "TEST-D-001",
            "subject": "Invoice INV-2024-8891 from Acme Corp",
            "sender_email": "billing@acmecorp.com",
            "sender_name": "Acme Billing",
            "body": "Please find attached invoice INV-2024-8891 for $4,500.00 due on September 30, 2026.",
        }

        self.assertFalse(is_system_notification(email))
        detection = detect_system_notification(email)
        self.assertFalse(detection["is_system_notification"])

        # Check router routes to invoice agent
        analysis = {
            "email_type": "invoice",
            "priority": "medium",
            "recommended_action": "route_to_invoice_agent",
        }
        mock_inv = MagicMock(return_value={"agent": "invoice_agent", "status": "ROUTED"})
        with patch.dict(agent_router.routes, {"route_to_invoice_agent": mock_inv}):
            routing = route_email(email, analysis)
            mock_inv.assert_called_once()
            self.assertEqual(routing["agent"], "invoice_agent")

    def test_scenario_e_normal_technical_email(self):
        """
        Scenario E: Normal technical/general email
        EXPECTED: still reaches appropriate existing agent (rag_agent).
        """
        email = {
            "email_id": "TEST-E-001",
            "subject": "How to create SR & Invoice in GSVAI Fusion?",
            "sender_email": "operations.lead@clientcompany.com",
            "sender_name": "Operations Team",
            "body": "Hi, could you guide us on the exact steps to create a Service Request and link it to an AP Invoice?",
        }

        self.assertFalse(is_system_notification(email))
        detection = detect_system_notification(email)
        self.assertFalse(detection["is_system_notification"])

        # Router with technical_issue or general_query routes to rag_agent
        analysis = {
            "email_type": "general_query",
            "priority": "medium",
            "recommended_action": "route_to_rag_agent",
        }
        mock_rag = MagicMock(return_value={"agent": "rag_agent", "status": "ROUTED"})
        with patch.dict(agent_router.routes, {"route_to_rag_agent": mock_rag}):
            routing = route_email(email, analysis)
            mock_rag.assert_called_once()
            self.assertEqual(routing["agent"], "rag_agent")

    def test_scenario_f_email_service_bypasses_groq_for_ndr(self):
        """
        Verifies EmailService.analyze_email_by_id and route_email_by_id:
        - Groq LLM is NOT invoked for NDR
        - Database updated to SYSTEM_NOTIFICATION
        - route_email_by_id returns system_notification
        """
        from services.email_service import EmailService

        service = EmailService()

        fake_ndr_email = {
            "EMAIL_ID": "TEST-NDR-001",
            "MESSAGE_ID": "MSG-NDR-001",
            "SUBJECT": "Undeliverable: RE: How to Create SR & Invoice",
            "SENDER_EMAIL": "MicrosoftExchange329e71ec88ae4615bbc36ab6ce41109e@GSVAIEnterpriseAI.onmicrosoft.com",
            "BODY": "Delivery has failed to these recipients or groups. 550 5.1.1 Recipient not found.",
            "STATUS": "INGESTED",
        }

        with patch.object(service.repository, "get_email", return_value=fake_ndr_email), \
             patch.object(service.analysis_repository, "create_analysis") as mock_create_analysis, \
             patch.object(service.analysis_repository, "get_analysis", return_value={"email_type": "system_notification", "priority": "low"}), \
             patch.object(service.repository, "update_email") as mock_update_email, \
             patch("services.email_service.analyze_email") as mock_groq:

            analysis = service.analyze_email_by_id("TEST-NDR-001")

            # Groq LLM MUST NOT be called
            mock_groq.assert_not_called()

            # Result must be system_notification
            self.assertEqual(analysis["email_type"], "system_notification")
            self.assertEqual(analysis["priority"], "low")

            # Database updated to SYSTEM_NOTIFICATION
            mock_update_email.assert_called_once()
            call_kwargs = mock_update_email.call_args[1]
            self.assertEqual(call_kwargs["status"], "SYSTEM_NOTIFICATION")
            self.assertEqual(call_kwargs["routed_agent"], "system_notification")

        with patch.object(service.repository, "get_email", return_value={**fake_ndr_email, "EMAIL_TYPE": "system_notification", "STATUS": "SYSTEM_NOTIFICATION"}), \
             patch.object(service.repository, "update_email") as mock_update_email_route:

            routing = service.route_email_by_id("TEST-NDR-001")
            self.assertEqual(routing["routing"]["agent"], "system_notification")
            self.assertEqual(routing["routing"]["status"], "SYSTEM_NOTIFICATION")

    def test_scenario_g_email_automation_service_guards_and_trace(self):
        """
        Verifies EmailAutomationService:
        - 15-stage trace properly annotates NDR bypass
        - approve_and_reply throws ValueError preventing sending reply to NDR
        """
        from services.email_automation_service import EmailAutomationService

        service = EmailAutomationService()

        # Check trace generation with status="SYSTEM_NOTIFICATION"
        trace = service._build_trace(
            email={
                "email_id": "EMAIL-NDR-TEST",
                "subject": "Undeliverable: RE: Urgent",
                "sender_email": "MicrosoftExchange123@GSVAIEnterpriseAI.onmicrosoft.com",
            },
            analysis={
                "email_type": "system_notification",
                "priority": "low",
                "recommended_action": "ignore_system_notification",
                "reasoning_summary": "Microsoft Exchange NDR sender & subject: Undeliverable",
            },
            routing={
                "agent": "system_notification",
                "action": "ignore_system_notification",
            },
            status="SYSTEM_NOTIFICATION",
        )

        self.assertIsInstance(trace, list)
        self.assertEqual(len(trace), 15)

        # Step 4 must be Deterministic System Filter
        step4 = next(s for s in trace if s["step"] == 4)
        self.assertEqual(step4["status"], "completed")
        self.assertIn("Bypassed Groq LLM", step4["details"]["ai_action"])

        # Step 7 (Semantic Search) must be skipped
        step7 = next(s for s in trace if s["step"] == 7)
        self.assertEqual(step7["status"], "skipped")

        # Step 14 (Microsoft Graph Reply) must be skipped
        step14 = next(s for s in trace if s["step"] == 14)
        self.assertEqual(step14["status"], "skipped")
        self.assertIn("prohibited", step14["summary"].lower())

        # Check approve_and_reply safety guard
        fake_email = {
            "EMAIL_ID": "EMAIL-NDR-TEST",
            "STATUS": "SYSTEM_NOTIFICATION",
            "ROUTED_AGENT": "system_notification",
            "SENDER_EMAIL": "MicrosoftExchange123@GSVAIEnterpriseAI.onmicrosoft.com",
            "SUBJECT": "Undeliverable: RE: Urgent",
        }

        with patch.object(service.email_service.repository, "get_email", return_value=fake_email):
            with self.assertRaises(ValueError) as ctx:
                service.approve_and_reply("EMAIL-NDR-TEST", "Here is a reply")
            self.assertIn("Outbound replies to system mailer-daemons are prohibited", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
