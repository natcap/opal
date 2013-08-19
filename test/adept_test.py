import adept

import invest_natcap.testing

class AdeptTest(invest_natcap.testing.GISTest):
    def test_smoke(self):
        """A simple smoke test for adept."""
        adept.execute({})
