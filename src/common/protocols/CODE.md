# Code

Trace the real caller and look for an existing mechanism before adding another. Repair, simplify or replace that mechanism according to the problem. Bring necessary emergency repairs back into maintained source.

## Boundaries

Keep decisions easy to test and external I/O easy to locate. Pure functions work well for transformations and decisions; adapters handle files, network, clocks and processes. Follow the project's existing architecture and split jobs that need independent failure or recovery handling.

Use concurrent I/O when calls are independent, with appropriate timeouts and cancellation. A short synchronous operation does not need a new asynchronous subsystem. Choose a boundary because it improves the change, not to satisfy a universal file pattern.

## Size and dependencies

Write the simplest code that provides the requested behavior. Add a dependency, option or abstraction for a current use. A large file may need splitting when the change exposes unclear responsibilities; avoid unrelated refactors during a bounded repair.

## Tests

For a defect, preserve the failing scenario and make it pass. Test at the layer where the defect happens. Run directly affected checks while editing and applicable project checks before delivery.

The repository's coverage marker names source paths on a test file's first line:

```text
# LHC:COVERS src/billing/price.py src/billing/tax.py
// LHC:COVERS internal/price/price.go
```

Find relevant marked tests with `rg -l "LHC:COVERS.*<path>"`. Keep these mappings current. A marker helps discovery; actual test behavior establishes coverage.

## Existing service marks

Use `LHC:<KIND> <key=value ...> <text>` where the project needs a searchable maintenance note:

| Mark | Meaning |
| --- | --- |
| `LHC:COVERS <paths>` | Source paths checked by a test file |
| `LHC:LEGACY remove=YYYY-MM-DD <replacement>` | Old implementation retained for a specific migration |
| `LHC:BLOCKING <reason>` | An intentionally blocking external call worth explaining |

Review a legacy path when the task touches it or a maintenance task selects it. Retire it once its users have migrated. An expired note does not silently enlarge every unrelated feature task.
