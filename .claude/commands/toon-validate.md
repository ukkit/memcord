# TOON Validate

Validate TOON v2.0 files for correctness.

**Usage:** `/toon-validate <file> [--strict]`

**Options:**
- `--strict` - Enable strict mode validation (production)
- Default - Lenient mode (warnings only)

Execute the following workflow:

### 1. Validate Input

```bash
FILE="$1"

if [[ -z "$FILE" ]]; then
  echo "Usage: /toon-validate <file> [--strict]"
  echo "Example: /toon-validate data.toon --strict"
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "❌ Error: File not found: $FILE"
  exit 1
fi

echo "Validating: $FILE"
```

### 2. Check Binary

```bash
TOON_BIN=".claude/utils/toon/zig-out/bin/toon"

if [[ ! -f "$TOON_BIN" ]]; then
  echo "❌ Zig binary not found"
  echo "Build it with:"
  echo "  cd .claude/utils/toon && zig build -Doptimize=ReleaseFast"
  exit 1
fi
```

### 3. Run Validation

```bash
STRICT_FLAG=""
if [[ "$2" == "--strict" ]]; then
  STRICT_FLAG="--strict"
  echo "Mode: Strict (errors block)"
else
  echo "Mode: Lenient (warnings only)"
fi

echo ""
$TOON_BIN validate "$FILE" $STRICT_FLAG
EXIT_CODE=$?
```

### 4. Report Results

```bash
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
  echo "✅ File is valid TOON v2.0"
  exit 0
elif [[ $EXIT_CODE -eq 2 ]]; then
  echo "⚠️  File has warnings (see above)"
  echo ""
  echo "To enforce strict validation:"
  echo "  /toon-validate $FILE --strict"
  exit 0
else
  echo "❌ File has errors (see above)"
  echo ""
  echo "Common fixes:"
  echo "  • Add array counts: {fields}: → [N]{fields}:"
  echo "  • Fix indentation to multiples of 2"
  echo "  • Remove invalid escape sequences"
  echo "  • Match row count to declared count"
  exit 1
fi
```

## Validation Rules

### Strict Mode Checks

1. **Indentation** - Must be multiples of 2 spaces, no tabs
2. **Array Counts** - `[N]` must match actual row count
3. **Field Width** - All rows must have same number of fields
4. **No Blank Lines** - Within arrays
5. **Valid Escapes** - Only `\\ \" \n \r \t`

### Common Errors

**Indentation Error:**
```
❌ Line 3: Indentation must be multiple of 2 (found 3)
```

**Count Mismatch:**
```
❌ Array declared [5] but found 3 rows
```

**Invalid Escape:**
```
❌ Line 1: Invalid escape sequence '\u'
Valid: \\ \" \n \r \t
```

## Related Commands

- `/toon-encode` - JSON → TOON
- `/toon-decode` - TOON → JSON (TODO)

## See Also

- **Strict Mode Guide:** `.claude/utils/toon/examples/strict-mode.md`
- **Validation Rules:** `.claude/docs/toon-guide.md#validation`
