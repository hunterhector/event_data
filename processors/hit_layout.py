"""
Create a HIT layout with provided URL
"""

import xml.etree.ElementTree as ET
from pathlib import Path


class HITLayout:

    QUESTION_SCHEMA = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2017-11-06/QuestionForm.xsd"
    URL_FORMAT = "<![CDATA[Link to the task: <a href='%s' target='_blank'>%s</a>]]>"

    def __init__(self, template_dir: str, website_url: str) -> None:
        self.template_path = Path(template_dir) / "template.xml"
        self.website_url = website_url

        self._load_template()
        self._create_layout()

    def _load_template(self) -> None:
        self.xml = ET.parse(self.template_path)
        self.xml_root = self.xml.getroot()

    def _create_layout(self) -> None:
        self.xml_root.find("Overview").findall("FormattedContent")[
            -1
        ].text = self.URL_FORMAT % (self.website_url, self.website_url)
        self.xml_root.attrib["xmlns"] = self.QUESTION_SCHEMA

    def get_hit_string(self) -> str:
        return (
            ET.tostring(self.xml_root)
            .decode("utf-8")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

    def write_xml(self, out_path):
        self.xml.write(out_path)
