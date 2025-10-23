import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

class DrugBankParser:
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()
        self.ns = {'db': 'http://www.drugbank.ca'}

    def search_drugs(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for drug in self.root.findall('db:drug', self.ns):
            name = drug.find('db:name', self.ns)
            if name is not None and query.lower() in name.text.lower():
                drug_id = drug.find('db:drugbank-id', self.ns)
                description = drug.find('db:description', self.ns)
                targets = [t.find('db:name', self.ns).text for t in drug.findall('db:targets/db:target', self.ns) if t.find('db:name', self.ns) is not None]
                results.append({
                    'id': drug_id.text if drug_id is not None else '',
                    'name': name.text,
                    'description': description.text if description is not None else '',
                    'targets': targets,
                    'url': f'https://go.drugbank.com/drugs/{drug_id.text}' if drug_id is not None else ''
                })
        return results

    def get_drug_by_id(self, drugbank_id: str) -> Dict[str, Any]:
        for drug in self.root.findall('db:drug', self.ns):
            ids = [i.text for i in drug.findall('db:drugbank-id', self.ns)]
            if drugbank_id in ids:
                name = drug.find('db:name', self.ns)
                description = drug.find('db:description', self.ns)
                targets = [t.find('db:name', self.ns).text for t in drug.findall('db:targets/db:target', self.ns) if t.find('db:name', self.ns) is not None]
                return {
                    'id': drugbank_id,
                    'name': name.text if name is not None else '',
                    'description': description.text if description is not None else '',
                    'targets': targets,
                    'url': f'https://go.drugbank.com/drugs/{drugbank_id}'
                }
        return {}
