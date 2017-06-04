import requests
url = "https://api.github.com/repos/urschrei/pyzotero/contributors"
result = requests.get(url)
result.raise_for_status()
as_dict = result.json()
# remove me from the list
as_dict.pop(0)
header = "# This is the list of people (as distinct from AUTHORS) who have contributed code to Pyzotero.\n\n| **Commits** | **Contributor**<br/> |\n| --- |--- |\n"
template = "| {contributions} | [{login}]({html_url}) |\n"
formatted = (template.format(**dct) for dct in as_dict)
with open("CONTRIBUTORS", 'w') as f:
    f.write(header)
    for item in formatted:
        f.write(item)
