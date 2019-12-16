# Contribution Guidelines

## Reporting issues

- **Search for existing issues.** Please check to see if someone else has reported the same issue.
- **Share as much information as possible.** Include operating system and version, browser and version. Also, include steps to reproduce the bug.

## Project Setup
Refer to the [README](README.md).

## Code Style

This code generally tries to adhere to [PEP-8]( <https://www.python.org/dev/peps/pep-0008/>) standards for style, howevever we emphasize the PEP-8 team's point that "A Foolish Consistency is the Hobgoblin of Little Minds". From their website...

*Some other good reasons to ignore a particular guideline:*

* When applying the guideline would make the code less readable, even for someone who is used to reading code that follows this PEP.
* To be consistent with surrounding code that also breaks it (maybe for historic reasons) -- although this is also an opportunity to clean up someone else's mess (in true XP style).
* Because the code in question predates the introduction of the guideline and there is no other reason to be modifying that code.
* When the code needs to remain compatible with older versions of Python that don't support the feature recommended by the style guide.

## Testing
Use the material provided in the [demo]( <https://github.com/wingtorres/morphometrix/blob/master/demo>)  directory for testing

## Pull requests
- Try not to pollute your pull request with unintended changes – keep them simple and small. If possible, squash your commits.
- Try to share how your code has been tested before submitting a pull request.
- If your PR resolves an issue, include **closes #ISSUE_NUMBER** in your commit message (or a [synonym](https://help.github.com/articles/closing-issues-via-commit-messages)).
- Review
    - If your PR is ready for review, another contributor will be assigned to review your PR
    - The reviewer will accept or comment on the PR. 
    - If needed address the comments left by the reviewer. Once you're ready to continue the review, ping the reviewer in a comment.
    - Once accepted your code will be merged to `master`
