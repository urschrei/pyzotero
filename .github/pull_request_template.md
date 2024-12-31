Thanks for opening a PR. Please read the following:

- **Base your changes on the `main` branch**
    - If necessary, rebase against `main` before opening a pull request
- Follow [PEP 8](http://www.python.org/dev/peps/pep-0008/). I run [`ruff`](https://docs.astral.sh/ruff/) against the codebase and perhaps you should, too
- Use spaces for indentation, and ensure that all methods have a proper docstring. **Please don't use Doctest**
- If at all possible, don't add dependencies
    - If it's unavoidable, ensure that the dependency is maintained, and supported
    - Ensure that you add your dependency to [pyproject.toml](pyproject.toml)
- Run the tests, and ensure that they pass. If you're adding a feature, **you must add tests that exercise it**
- If your pull request is a feature, **document it**
- One feature per pull request
- If possible, [squash](http://git-scm.com/book/en/Git-Tools-Rewriting-History#Squashing-Commits) your commits before opening a pull request, unless it makes no sense to do so
- If in doubt, comment your code.

## License of Contributed Code
Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you shall be licensed under the Blua Oak Model License 1.0, without any additional terms or conditions.  
Please note that pull requests with licenses that are more restrictive than or otherwise incompatible with the license will not be accepted.