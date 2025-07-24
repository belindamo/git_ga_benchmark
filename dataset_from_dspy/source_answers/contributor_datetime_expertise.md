# Contributor Knowledge: Datetime Serialization Expertise

## Question
I have a datetime serialization bug in adapters. Who is the most knowledgeable person on this part of the codebase, based on their past commits and reviews?

## Correct Answer

**@dbczumar** has deep expertise - authored [PR #1853](https://github.com/stanfordnlp/dspy/pull/1853) fixing Pydantic datetime/enum serialization issues. 

**@chenmoneygithub** handles async adapter integration.

### To verify their contributions:
Use `git blame dspy/adapters/*.py` and `git log --author=dbczumar -- dspy/adapters/` to see their specific contributions to serialization logic.

## Source Evidence with Links

- [PR #1853](https://github.com/stanfordnlp/dspy/pull/1853) technical depth on Pydantic serialization by @dbczumar
- Git blame analysis: `git shortlog -sn -- dspy/adapters/`
- Commit authorship patterns and review history

## Key Points

1. **Primary Expert**: @dbczumar for Pydantic datetime/enum serialization (PR #1853)
2. **Secondary Expert**: @chenmoneygithub for async adapter integration
3. **Verification Method**: Use git blame and git log to confirm contributions
4. **Specific Expertise**: Focus on Pydantic serialization issues, not general adapter logic
5. **Evidence-Based**: Recommendation based on actual commit history and technical depth 