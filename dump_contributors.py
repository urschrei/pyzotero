import io
import requests

url = "https://api.github.com/repos/urschrei/pyzotero/contributors"
result = requests.get(url)
result.raise_for_status()
as_dict = result.json()
# remove me from the list
as_dict.pop(0)
header = u"# This is the list of people (as distinct from [AUTHORS](AUTHORS)) who have contributed code to Pyzotero.\n\n| **Commits** | **Contributor**<br/> |\n| --- |--- |\n"
template = u"| {contributions} | [{login}](https://github.com/urschrei/pyzotero/commits?author={login}) |\n"
with io.open("CONTRIBUTORS.md", "w", encoding="utf-8") as f:
    f.write(header)
    f.writelines(template.format(**dct) for dct in as_dict)
