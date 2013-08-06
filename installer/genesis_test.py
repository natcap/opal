import unittest
import genesis

class GenesisTest(unittest.TestCase):
    def test_start_menu(self):
        start_menu_options = [
            {
                "name": "{name}",
                "target": "launch_adept.exe",
                "icon": "{icon}",
            },
            {
                "name": "{name} Documentation",
                "target": "adept_documentation.docx",
            },
        ]

        start_menu_links = genesis.start_menu_links(start_menu_options)

        print start_menu_links
