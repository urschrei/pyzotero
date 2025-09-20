import httpx

url = "https://api.github.com/repos/urschrei/pyzotero/contributors"
result = httpx.get(url)
result.raise_for_status()
contributors = result.json()
# filter out dependabot and meeee
as_dict = [
    contributor
    for contributor in contributors[1:]
    if not contributor["login"].lower().startswith("dependabot")
]
header = "# This is the list of people (as distinct from [AUTHORS](AUTHORS)) who have contributed code to Pyzotero.\n\n| **Commits** | **Contributor**<br/> |\n| --- |--- |\n"
template = "| {contributions} | [{login}](https://github.com/urschrei/pyzotero/commits?author={login}) |\n"
with open("CONTRIBUTORS.md", "w", encoding="utf-8") as f:
    f.write(header)
    f.writelines(template.format(**dct) for dct in as_dict)
