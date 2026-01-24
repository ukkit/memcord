# TOON Decode

Convert TOON v2.0 format back to JSON using the Zig decoder.

**Usage:** `/toon-decode <file> [options]`

**Options:**
- `--strict` - Enable strict mode validation during decoding
- `--no-expand-paths` - Don't expand folded paths (keep dot notation)

Execute the following workflow:

### 1. Validate Input

```bash
FILE="$1"

if [[ -z "$FILE" ]]; then
  echo "Usage: /toon-decode <file> [options]"
  echo "Example: /toon-decode data.toon"
  echo "Example: /toon-decode data.toon --strict"
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "❌ Error: File not found: $FILE"
  exit 1
fi

if [[ ! "$FILE" =~ \.toon$ ]]; then
  echo "⚠️  Warning: File doesn't have .toon extension"
  read -p "Continue? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
  fi
fi

echo "✓ Input: $FILE"
```

### 2. Parse Options

```bash
STRICT_FLAG=""
EXPAND_PATHS_FLAG=""
OUTPUT="${FILE%.toon}.json"

shift  # Remove first arg (filename)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT_FLAG="--strict"
      shift
      ;;
    --no-expand-paths)
      EXPAND_PATHS_FLAG="--no-expand-paths"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

echo "⚙️  Configuration:"
echo "  Strict mode: ${STRICT_FLAG:-disabled}"
echo "  Path expansion: ${EXPAND_PATHS_FLAG:-enabled (default)}"
echo "  Output: $OUTPUT"
```

### 3. Check Zig Binary

```bash
TOON_BIN=".claude/utils/toon/zig-out/bin/toon"

if [[ ! -f "$TOON_BIN" ]]; then
  echo "❌ Zig binary not found. Building..."
  echo ""
  cd .claude/utils/toon
  /opt/homebrew/opt/zig@0.14/bin/zig build -Doptimize=ReleaseFast
  cd -
  echo ""
  echo "✓ Build complete"
fi
```

### 4. Decode

```bash
echo ""
echo "Decoding..."

$TOON_BIN decode "$FILE" \
  $STRICT_FLAG \
  $EXPAND_PATHS_FLAG \
  > "$OUTPUT"

if [[ $? -eq 0 ]]; then
  echo "✓ Decoding successful"
else
  echo "❌ Decoding failed"
  exit 1
fi
```

### 5. Validate JSON

```bash
# Verify JSON is valid
if command -v python3 &> /dev/null; then
  python3 -m json.tool "$OUTPUT" > /dev/null 2>&1
  if [[ $? -eq 0 ]]; then
    echo "✓ JSON validation passed"
  else
    echo "⚠️  Warning: Output may not be valid JSON"
  fi
fi
```

### 6. Show Results

```bash
JSON_SIZE=$(wc -c < "$OUTPUT")
TOON_SIZE=$(wc -c < "$FILE")
JSON_TOKENS=$((JSON_SIZE / 4))
TOON_TOKENS=$((TOON_SIZE / 4))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Conversion Results:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TOON: ~$TOON_TOKENS tokens ($TOON_SIZE bytes)"
echo "  JSON: ~$JSON_TOKENS tokens ($JSON_SIZE bytes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Output: $OUTPUT"
echo ""
echo "Preview (first 10 lines):"
head -10 "$OUTPUT"
```

## Examples

### Basic Decoding
```bash
/toon-decode data.toon
# Outputs: data.json
```

### Strict Mode
```bash
/toon-decode data.toon --strict
# Validates during decoding, fails on format errors
```

### Keep Folded Paths
```bash
/toon-decode data.toon --no-expand-paths
# Keeps "server.host" instead of expanding to {"server": {"host": ...}}
```

## Path Expansion

By default, the decoder expands folded paths:

**TOON Input:**
```
server.host: localhost
server.port: 8080
database.host: db.example.com
database.port: 5432
```

**JSON Output (default):**
```json
{
  "server": {
    "host": "localhost",
    "port": 8080
  },
  "database": {
    "host": "db.example.com",
    "port": 5432
  }
}
```

**JSON Output (--no-expand-paths):**
```json
{
  "server.host": "localhost",
  "server.port": 8080,
  "database.host": "db.example.com",
  "database.port": 5432
}
```

## Supported Formats

The decoder supports all TOON v2.0 features:

**Tabular Arrays:**
```
[3]{id,name,age}:
  1,Alice,30
  2,Bob,25
  3,Carol,35
```

**Inline Arrays:**
```
tags[5]: javascript,react,node,express,api
```

**Expanded Lists:**
```
- name: Alice
  role: admin
- name: Bob
  role: user
```

**Three Delimiters:**
- Comma: `[N]{fields}:`
- Tab: `[N\t]{fields}:`
- Pipe: `[N|]{fields}:`

## Related Commands

- `/toon-encode` - JSON → TOON
- `/toon-validate` - Validate TOON file
- `/analyze-tokens` - Compare formats

## See Also

- **User Guide:** `.claude/docs/toon-guide.md`
- **Decoder Implementation:** `.claude/utils/toon/toon.zig`
- **FAQ:** `.claude/docs/FAQ.md`
