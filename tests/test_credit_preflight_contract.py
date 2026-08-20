import unittest

from scripts.estimate_cost import preflight_cost


class FakeCreditClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, path, body):
        self.calls.append((path, body))
        return self.response


class CreditPreflightContractTests(unittest.TestCase):
    def test_enterprise_preflight_separates_usage_from_zero_client_charge(self):
        client = FakeCreditClient({
            "internalEstimatedUsageClip": 14.8501,
            "clientCreditChargeClip": 0,
            "settlementMode": "enterprise_usage_only",
            "affordable": True,
            "approvalCapClip": 15,
            "withinApprovalCap": True,
            "spendLimitViolation": None,
            "units": "clip",
            "balanceClip": 999,
        })
        body = {
            "operationType": "lambda_render",
            "provider": "aws_lambda",
            "metrics": {"videoSeconds": 68.54},
            "maxCredits": 15,
        }

        result = preflight_cost(client, body)

        self.assertEqual(result["internalEstimatedUsageClip"], 14.8501)
        self.assertEqual(result["clientCreditChargeClip"], 0)
        self.assertNotIn("balanceClip", result)
        self.assertEqual(client.calls, [("/api/v1/credits/preflight", body)])


if __name__ == "__main__":
    unittest.main()
