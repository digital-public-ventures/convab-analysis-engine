# GitHub Copilot Instructions for this Project

## Terminal Command Best Practices

### CRITICAL: ALWAYS use built-in file creation/editing capabilities like `create_file` NEVER use terminal commands like heredoc for file creation

**Never use `cat > filename << 'EOF' ... EOF` to create scripts or files in the terminal.** Instead use your built-in file creation and editing capabilities FOR ALL FILE CREATION TASKS. Trying to write multi-line files via terminal commands is error-prone and unreliable.

### Background Process Management

The VSCode RunInTerminal function's `isBackground` argument does not create a background process. It simply creates a new terminal. It is critical to use `isBackground: true` to create a new terminals when you already have an existing process and you want to sleep or check on it.

1. **You should prefer writing stdout/stderr to file instead of using `get_terminal_output`**
   - Stream logs to a logs folder and read from there
   - Use `get_terminal_output` only for quick status checks

2. **ALWAYS check if a process is running in a terminal before executing new commands**
   - Use `get_terminal_output` to check the state of any active terminals
   - Never run commands in a terminal that has a background process running
   - If there is a process running, use `isBackground: true` to open a new terminal to sleep or check status

3. **Never use `sleep` command without specifying `isBackground: true`**
   - If you don't use `isBackground: true`, it will interrupt the current process with SIGINT
   - Instead, use `isBackground: true` to wait asynchronously

4. **For sequential operations requiring wait time:**
   - Always use `isBackground: true` for the second and all future commands
   - Use `get_terminal_output` to check status
   - Run subsequent commands in a fresh terminal session that uses `isBackground: true`

5 **Clean up unused terminals:**

- After a background process is complete and you have gathered necessary output, close the terminal to free up resources
- This helps avoid confusion and resource leaks

## ⚠️ CRITICAL: Knowledge Cutoff Date Warning

**My knowledge was last updated in April 2024. 18 months have elapsed and it is now December 2025.** This means:

- **I DO NOT know about bleeding-edge best practices, AI models, API versions (e.g. Airtable, Google-Genai), or changes to libraries**
- **I MUST use the OpenAI Responses API documentation** in `.github/openai-responses-api-reference/` for all OpenAI-related code
- **I MUST use web search** to validate assumptions about:
  - Anything related to AI models and APIs
  - API endpoint usage (all APIs that are likely to change over 18 months, which is most of them)
  - Library versions and breaking changes (again 18 months have passed)
  - Framework updates and best practices
- **I MUST NOT assume** that chat completions API or any other API I know about is still current
- **I MUST read existing docs in /docs** in the repository to ensure that I see the most relevant up-to-date information
- **I MUST document new info I discover via web search** in the /docs folder for future reference
- **When in doubt, ASK** the user to confirm current standards rather than assuming

## Documentation Usage Instructions

- **I MUST use the documentation in the `/docs` folder** for any relevant information about the project
- **I MUST NOT assume** that my prior knowledge about libraries, APIs, or frameworks is current
- **I MUST read and incorporate** any relevant information from the documentation into my code and responses
- **I MUST update the documentation** with any new information I discover during web searches or user interactions
