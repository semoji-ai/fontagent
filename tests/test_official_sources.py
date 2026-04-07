from __future__ import annotations

import unittest

from fontagent.official_sources import _parse_gongu_license


class GonguLicenseParsingTests(unittest.TestCase):
    def test_parse_gongu_kogl_type1_without_je_prefix(self) -> None:
        parsed = _parse_gongu_license("공공누리 1유형 이용조건: 출처표시")
        self.assertEqual(parsed, ("kogl-type1", True, True, True, False))

    def test_parse_gongu_kogl_type2_without_je_prefix(self) -> None:
        parsed = _parse_gongu_license("공공누리 2유형 이용조건: 출처표시 + 상업적 이용금지")
        self.assertEqual(parsed, ("kogl-type2", False, False, False, False))


if __name__ == "__main__":
    unittest.main()
