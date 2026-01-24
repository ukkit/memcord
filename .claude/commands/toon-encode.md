# TOON Encode

Convert JSON to TOON v2.0 format using the Zig encoder.

**Usage:** `/toon-encode <file> [options]`

**Options:**
- `--delimiter comma|tab|pipe` - Delimiter choice (default: comma)
- `--key-folding` - Enable key folding (default: on)
- `--no-key-folding` - Disable key folding
- `--check-only` - Just analyze, don't convert

Execute the following workflow:

### 1. Validate Input

```bash
FILE="$1"

if [[ -z "$FILE" ]]; then
  echo "Usage: /toon-encode <file> [options]"
  echo "Example: /toon-encode data.json --delimiter tab"
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "❌ Error: File not found: $FILE"
  exit 1
fi

if [[ ! "$FILE" =~ \.json$ ]]; then
  echo "⚠️  Warning: File doesn't have .json extension"
  read -p "Continue? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
  fi
fi

echo "✓ Input: $FILE"
```

### 2. Check Suitability (if --check-only)

```bash
if [[ "$2" == "--check-only" ]]; then
  echo "Analyzing data..."
  .claude/utils/toon/zig-out/bin/toon check "$FILE"
  exit $?
fi
```

### 3. Parse Options

```bash
DELIMITER="comma"
KEY_FOLDING="--key-folding"
OUTPUT="${FILE%.json}.toon"

while [[ $# -gt 1 ]]; do
  case "$2" in
    --delimiter)
      DELIMITER="$3"
      shift 2
      ;;
    --no-key-folding)
      KEY_FOLDING=""
      shift
      ;;
    --key-folding)
      KEY_FOLDING="--key-folding"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

echo "⚙️  Configuration:"
echo "  Delimiter: $DELIMITER"
echo "  Key folding: ${KEY_FOLDING:-disabled}"
echo "  Output: $OUTPUT"
```

### 4. Check Zig Binary

```bash
TOON_BIN=".claude/utils/toon/zig-out/bin/toon"

if [[ ! -f "$TOON_BIN" ]]; then
  echo "❌ Zig binary not found. Building..."
  echo ""
  cd .claude/utils/toon
  zig build -Doptimize=ReleaseFast
  cd -
  echo ""
  echo "✓ Build complete"
fi
```

### 5. Convert

```bash
echo ""
echo "Converting..."

$TOON_BIN encode "$FILE" \
  --delimiter "$DELIMITER" \
  $KEY_FOLDING \
  > "$OUTPUT"

if [[ $? -eq 0 ]]; then
  echo "✓ Conversion successful"
else
  echo "❌ Conversion failed"
  exit 1
fi
```

### 6. Calculate Savings

```bash
JSON_SIZE=$(wc -c < "$FILE")
TOON_SIZE=$(wc -c < "$OUTPUT")
SAVED=$((JSON_SIZE - TOON_SIZE))
PERCENT=$((SAVED * 100 / JSON_SIZE))

JSON_TOKENS=$((JSON_SIZE / 4))
TOON_TOKENS=$((TOON_SIZE / 4))
SAVED_TOKENS=$((JSON_TOKENS - TOON_TOKENS))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Token Savings:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JSON:  ~$JSON_TOKENS tokens ($JSON_SIZE bytes)"
echo "  TOON:  ~$TOON_TOKENS tokens ($TOON_SIZE bytes)"
echo "  Saved: ~$SAVED_TOKENS tokens ($PERCENT%)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Output: $OUTPUT"
```

### 7. Validate (Optional)

```bash
echo ""
echo "Validating output..."
$TOON_BIN validate "$OUTPUT" --strict

if [[ $? -eq 0 ]]; then
  echo "✓ Validation passed"
else
  echo "⚠️  Validation warnings (see above)"
fi
```

## Related Commands

- `/toon-decode` - TOON → JSON (TODO: decoder not yet implemented)
- `/toon-validate` - Validate TOON file
- `/analyze-tokens` - Compare formats

## See Also

- **User Guide:** `.claude/docs/toon-guide.md`
- **Examples:** `.claude/utils/toon/examples/`
- **FAQ:** `.claude/docs/FAQ.md`
