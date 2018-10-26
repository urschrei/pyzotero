# Contributing
Contributions are welcome. Please bear the following in mind:

- **Base your changes on the dev branch**
    - If necessary, rebase against `dev` before opening a pull request
- Follow [PEP 8](http://www.python.org/dev/peps/pep-0008/). I currently periodically run [`Black`](https://black.readthedocs.io/en/stable/) against the codebase and perhaps you should, too
- Use spaces for indentation, and ensure that all methods have a proper docstring. **Please don't use Doctest**
- If at all possible, don't add dependencies
    - If it's unavoidable, ensure that the dependency is maintained, and supported
    - Ensure that you add your dependency to [setup.py](setup.py)
- Run the tests, and ensure that they pass. If you're adding a feature, **you must add tests that exercise it**
- If your pull request is a feature, **document it**
- One feature per pull request
- If possible, [squash](http://git-scm.com/book/en/Git-Tools-Rewriting-History#Squashing-Commits) your commits before opening a pull request, unless it makes no sense to do so
- If in doubt, comment your code.

## License of Contributed Code
Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you shall be MIT licensed, without any additional terms or conditions.  
Please note that pull requests with licenses that are more restrictive than or otherwise incompatible with the MIT license will not be accepted.
