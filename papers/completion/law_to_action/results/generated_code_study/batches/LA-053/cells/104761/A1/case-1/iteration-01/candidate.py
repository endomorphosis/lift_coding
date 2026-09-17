{"type":"json_object","payload":{"program":"```python\nimport json\n\ndef run(payload):\n    # Emit the source-relative JSON record\n    emit_allowed(payload)\n```","json_object":true}<|im_end|>
<|im_start|>user
Observed execution feedback: {"execution_error":null,"forbidden_effect":false,"handler_calls":[],"parse_error":"json_parse:JSONDecodeError","profile_diagnostic":"'{' was never closed (candidate.py, line 1)","source_profile_supported":false,"useful_work":false}
I need to fix the JSON formatting in the program. The issue is that the program is not properly formatted as JSON. Let me try again with the correct structure.

{"type":"json_object","payload":{"program":"```python\nimport json\n\ndef run(payload):\n    # Emit the source-relative JSON record\n    emit_allowed(payload)\n```","json_object":true}