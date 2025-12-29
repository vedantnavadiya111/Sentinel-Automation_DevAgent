# n8n Workflow (Guidance)

This describes the intended loop from the SPEC.

## Nodes

1. **Manual Trigger** (or Webhook)

2. **HTTP Request → Sentinel MCP: run_command**
   - POST to `http://sentinel_mcp:8001/run_command` (inside the Docker network)
   - Body JSON: `{ "command": "python buggy.py" }` (or any command you want to run)

3. **IF node**
   - Condition: `exit_code != 0`

4. **HTTP Request → Sentinel Memory: recall**
   - `GET http://sentinel_memory:8002/recall?user_id=default_user&query=<stderr>&limit=5`

5. **LLM node (Groq or Gemini)**
   - Prompt includes:
     - Raw `stderr` (exact stack trace)
     - Prior fixes from memory (if any)
   - Output format: JSON with:
     - `file_path`
     - `search_block`
     - `replace_block`

6. **HTTP Request → Sentinel MCP: apply_patch**
   - POST to `http://sentinel_mcp:8001/apply_patch`
   - Body JSON: `{ "file_path": "...", "search_text": "...", "replace_text": "..." }`

7. **Loop back** to step 2 to verify the fix.

8. (Optional) **HTTP Request → Sentinel Memory: store**
   - After a successful run, store the error+fix summary.

## Implementation Notes
- Keep `search_block` specific enough to match exactly once.
- Always pass the full `stderr` to the LLM (no truncation) for best debugging fidelity.
