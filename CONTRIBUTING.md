# Contributing
Contributions are welcome. Please bear the following in mind:

- Base your changes on the dev branch. If necessary, rebase against `dev` before opening a pull request
- Follow [PEP 8](http://www.python.org/dev/peps/pep-0008/), and the prevailing cultural conventions
- In particular, use spaces for indentation, and ensure that all methods have a proper docstring. Please don't use Doctest
- If at all possible, don't add dependencies. If it's unavoidable, ensure that the dependency is maintained, and supported. Ensure that you add your dependency to [setup.py](setup.py)
- Run the tests, and ensure that they pass. If you're adding a feature, try to add a test
- If your pull request is a feature, document it
- One feature per pull request
- If possible, [squash](http://git-scm.com/book/en/Git-Tools-Rewriting-History#Squashing-Commits) your commits before opening a pull request, unless it makes no sense to do so
- If in doubt, comment your code
