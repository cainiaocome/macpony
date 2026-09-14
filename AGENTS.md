# Repository instructions

## Documentation rules

1. Keep the documentation in `docs/` comprehensive and synchronized with the
   implemented protocol, Hammerspoon server, Python client, configuration,
   security model, and operational workflows. Update the relevant document in
   the same change whenever behavior or a public contract changes.
2. Document public interfaces in the source code. Lua service methods and
   lifecycle helpers should use LuaDoc comments, and the Python client’s public
   classes, methods, models, and exceptions should use docstrings or precise
   inline comments where behavior is non-obvious.

## Change discipline

- Preserve the single-client, local Unix-socket trust model unless a task
  explicitly changes it.
- Keep dangerous actions disabled by default and document any new capability or
  permission requirement.
- Run the relevant checks from `Makefile` before handing off changes.
