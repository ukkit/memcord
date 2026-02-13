"""Pre/Post summarizer-storage round-trip tests.

Feed 20 diverse, large text blocks through the full pipeline:
  text → TextSummarizer.summarize() → summary string
       → StorageManager.add_summary_entry(slot, text, summary)
       → StorageManager.read_memory(slot) → MemoryEntry
       → assert entry fields match pre-storage values exactly

Validates no data corruption or loss across all content types.
"""

import tempfile
from pathlib import Path

import pytest

from memcord.models import SearchQuery
from memcord.storage import StorageManager
from memcord.summarizer import TextSummarizer

# ---------------------------------------------------------------------------
# 20 diverse text blocks (each 500-5000+ chars)
# ---------------------------------------------------------------------------

TEXT_BLOCKS: list[tuple[str, str]] = [
    # 1. Unicode / emoji
    (
        "unicode_emoji",
        (
            "Hello world! \U0001f600\U0001f680\U0001f30d Here is a message with lots of "
            "Unicode content. Les caractères accentués sont très importants en français. "
            "日本語のテキストも含まれています。これはテスト用のテキストです。"
            "中文内容也是非常重要的，我们需要确保所有的字符都能正确处理。"
            "한국어도 포함되어야 합니다. 이것은 테스트 텍스트입니다. "
            "Ñoño está en España disfrutando de la piña colada. "
            "Ünlü bir türkçe metin yazıyoruz burada. "
            "\U0001f4a1 Key insight: Unicode handling must be robust across all encodings. "
            "\U0001f4ca Data shows that 60% of the world uses non-Latin scripts daily. "
            "\U0001f30f Global applications must handle: Arabic (العربية), Hebrew (עברית), "
            "Thai (ภาษาไทย), and Devanagari (हिन्दी). "
            "Emoji sequences: \U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466 "
            "\U0001f3f3\ufe0f\u200d\U0001f308 \U0001f1fa\U0001f1f8 "
            "Mathematical symbols: α β γ δ ε ζ η θ ι κ λ μ ν ξ π ρ σ τ. "
            "Currency symbols: € £ ¥ ₹ ₩ ₽ ₿. "
            "The application must preserve every single character without corruption. "
            "This block tests the full Unicode spectrum from BMP to supplementary planes."
        ),
    ),
    # 2. Multi-language code blocks
    (
        "multi_language_code",
        (
            "Here is a multi-language code review document.\n\n"
            "## Python Backend\n"
            "```python\n"
            "import asyncio\n"
            "from typing import Optional\n\n"
            "class DataProcessor:\n"
            "    def __init__(self, config: dict):\n"
            "        self.config = config\n"
            "        self._cache = {}\n\n"
            "    async def process(self, items: list[str]) -> list[dict]:\n"
            '        results = []\n'
            '        for item in items:\n'
            '            result = await self._transform(item)\n'
            '            results.append(result)\n'
            '        return results\n'
            "```\n\n"
            "## JavaScript Frontend\n"
            "```javascript\n"
            "const fetchData = async (endpoint) => {\n"
            "  try {\n"
            "    const response = await fetch(endpoint);\n"
            "    if (!response.ok) throw new Error(`HTTP ${response.status}`);\n"
            "    return await response.json();\n"
            "  } catch (err) {\n"
            "    console.error('Fetch failed:', err);\n"
            "    throw err;\n"
            "  }\n"
            "};\n"
            "```\n\n"
            "## SQL Queries\n"
            "```sql\n"
            "SELECT u.id, u.name, COUNT(o.id) AS order_count\n"
            "FROM users u\n"
            "LEFT JOIN orders o ON o.user_id = u.id\n"
            "WHERE u.created_at >= '2024-01-01'\n"
            "GROUP BY u.id, u.name\n"
            "HAVING COUNT(o.id) > 5\n"
            "ORDER BY order_count DESC\n"
            "LIMIT 100;\n"
            "```\n\n"
            "The Python code handles async data processing with caching. "
            "The JavaScript frontend fetches data with proper error handling. "
            "The SQL query joins users with orders and filters for active customers. "
            "All three languages show different paradigms but solve related problems."
        ),
    ),
    # 3. Chat transcript
    (
        "chat_transcript",
        (
            "User: Hi, I need help setting up a CI/CD pipeline for my Python project.\n"
            "Assistant: I'd be happy to help! What CI/CD platform are you using?\n"
            "User: We're using GitHub Actions. The project is a Django REST API.\n"
            "Assistant: Great choice! Here's what I recommend for your pipeline:\n"
            "1. Linting stage with ruff and mypy\n"
            "2. Testing stage with pytest and coverage\n"
            "3. Build stage for Docker image\n"
            "4. Deploy stage to staging/production\n"
            "User: That sounds good. How do I handle database migrations?\n"
            "Assistant: For migrations, you should run them as a separate step. "
            "Create a migration job that runs after the build but before deployment. "
            "Use Django's migrate command with proper environment variables.\n"
            "Human: What about secrets management?\n"
            "Claude: For secrets, use GitHub Actions secrets. Store your DATABASE_URL, "
            "SECRET_KEY, and API keys there. Reference them in your workflow with "
            "${{ secrets.SECRET_NAME }}.\n"
            "User: Should I use Docker multi-stage builds?\n"
            "Assistant: Absolutely! Multi-stage builds reduce your final image size. "
            "Use a builder stage with all dev dependencies for testing, then copy only "
            "the production artifacts to a slim runtime image. This can cut your image "
            "size by 60-80%.\n"
            "User: One more thing - how do I set up automatic rollbacks?\n"
            "Assistant: For rollbacks, implement health checks in your deployment. "
            "If the new version fails health checks within 5 minutes, automatically "
            "revert to the previous version. Use deployment strategies like blue-green "
            "or canary deployments for zero-downtime releases.\n"
            "User: Thanks, this is very helpful!\n"
            "Assistant: You're welcome! Remember to also set up monitoring and alerting "
            "for your production environment. Tools like Prometheus and Grafana work "
            "great with Django applications."
        ),
    ),
    # 4. Markdown document
    (
        "markdown_document",
        (
            "# Project Architecture Guide\n\n"
            "## Overview\n"
            "This document describes the **architecture** of our _microservices_ platform.\n\n"
            "## Components\n\n"
            "### API Gateway\n"
            "The API gateway handles all incoming requests and routes them to the "
            "appropriate service. It provides:\n"
            "- **Rate limiting** with configurable thresholds\n"
            "- *Authentication* via JWT tokens\n"
            "- Request/response transformation\n\n"
            "### Service Mesh\n"
            "We use [Istio](https://istio.io) for service-to-service communication. "
            "The mesh provides:\n"
            "1. Mutual TLS encryption\n"
            "2. Traffic management\n"
            "3. Observability\n\n"
            "### Data Layer\n\n"
            "| Service | Database | Purpose |\n"
            "|---------|----------|----------|\n"
            "| Users | PostgreSQL | User profiles and auth |\n"
            "| Orders | MongoDB | Order processing |\n"
            "| Cache | Redis | Session and query cache |\n"
            "| Search | Elasticsearch | Full-text search |\n\n"
            "## Deployment\n\n"
            "### Infrastructure as Code\n"
            "All infrastructure is managed through **Terraform** modules:\n"
            "- `modules/networking` — VPC, subnets, security groups\n"
            "- `modules/compute` — EKS cluster, node groups\n"
            "- `modules/storage` — RDS, S3 buckets\n\n"
            "### CI/CD Pipeline\n"
            "```mermaid\n"
            "graph LR\n"
            "    A[Commit] --> B[Build]\n"
            "    B --> C[Test]\n"
            "    C --> D[Deploy Staging]\n"
            "    D --> E[Deploy Production]\n"
            "```\n\n"
            "> **Note**: Always run integration tests before deploying to production.\n\n"
            "---\n"
            "Last updated: 2025-01-15 | Author: [Team Lead](mailto:lead@example.com)"
        ),
    ),
    # 5. HTML / XML fragments
    (
        "html_xml_fragments",
        (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n'
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "    <title>Dashboard &amp; Analytics</title>\n"
            '    <link rel="stylesheet" href="/css/main.css">\n'
            "</head>\n"
            "<body>\n"
            '    <header class="main-header" id="top">\n'
            '        <nav aria-label="Main navigation">\n'
            '            <a href="/" class="logo">MyApp&trade;</a>\n'
            '            <ul class="nav-links">\n'
            '                <li><a href="/dashboard">Dashboard</a></li>\n'
            '                <li><a href="/reports">Reports &raquo;</a></li>\n'
            "            </ul>\n"
            "        </nav>\n"
            "    </header>\n"
            '    <main class="content">\n'
            "        <section>\n"
            "            <h1>Welcome back, user!</h1>\n"
            "            <p>Your last login was <time>2025-01-15T14:30:00Z</time>.</p>\n"
            "            <p>Special chars: &lt;script&gt; &amp; &quot;quotes&quot; "
            "&apos;apostrophes&apos;</p>\n"
            "        </section>\n"
            "        <!-- XML configuration example -->\n"
            '        <?xml version="1.0" encoding="UTF-8"?>\n'
            '<config xmlns:app="http://example.com/app">\n'
            '    <app:setting name="timeout" value="30" />\n'
            '    <app:setting name="retries" value="3" />\n'
            "    <app:database>\n"
            "        <connection>postgresql://db:5432/myapp</connection>\n"
            "    </app:database>\n"
            "</config>\n"
            "    </main>\n"
            "</body>\n"
            "</html>"
        ),
    ),
    # 6. JSON content
    (
        "json_content",
        (
            "Here is the API response payload we received:\n\n"
            '{\n'
            '  "status": "success",\n'
            '  "data": {\n'
            '    "users": [\n'
            '      {\n'
            '        "id": 1,\n'
            '        "name": "Alice O\'Brien",\n'
            '        "email": "alice@example.com",\n'
            '        "roles": ["admin", "editor"],\n'
            '        "preferences": {\n'
            '          "theme": "dark",\n'
            '          "language": "en-US",\n'
            '          "notifications": {\n'
            '            "email": true,\n'
            '            "sms": false,\n'
            '            "push": true\n'
            '          }\n'
            '        },\n'
            '        "bio": "Loves coding & coffee ☕. Escaped \\"chars\\" here."\n'
            '      },\n'
            '      {\n'
            '        "id": 2,\n'
            '        "name": "Bob Smith",\n'
            '        "email": "bob@example.com",\n'
            '        "roles": ["viewer"],\n'
            '        "metadata": {\n'
            '          "login_count": 42,\n'
            '          "last_ip": "192.168.1.100",\n'
            '          "paths": ["C:\\\\Users\\\\bob", "/home/bob"],\n'
            '          "tags": ["new-user", "trial"]\n'
            '        }\n'
            '      }\n'
            '    ],\n'
            '    "pagination": {\n'
            '      "page": 1,\n'
            '      "per_page": 20,\n'
            '      "total": 150,\n'
            '      "total_pages": 8\n'
            '    }\n'
            '  },\n'
            '  "meta": {\n'
            '    "request_id": "req_abc123xyz",\n'
            '    "timestamp": "2025-01-15T14:30:00Z",\n'
            '    "version": "2.1.0"\n'
            '  }\n'
            '}\n\n'
            "The response contains user data with nested preferences and metadata. "
            "Note the special characters in bio fields and Windows paths in metadata."
        ),
    ),
    # 7. YAML config
    (
        "yaml_config",
        (
            "# Application Configuration\n"
            "# This YAML file controls all deployment settings\n\n"
            "app:\n"
            "  name: memcord-server\n"
            "  version: &version '2.4.1'\n"
            "  environment: production\n"
            "  debug: false\n\n"
            "server:\n"
            "  host: 0.0.0.0\n"
            "  port: 8080\n"
            "  workers: 4\n"
            "  timeout: 30\n"
            "  keepalive: 65\n\n"
            "database:\n"
            "  primary:\n"
            "    host: db-primary.internal\n"
            "    port: 5432\n"
            "    name: memcord_prod\n"
            "    pool_size: 20\n"
            "    max_overflow: 10\n"
            "  replica:\n"
            "    host: db-replica.internal\n"
            "    port: 5432\n"
            "    name: memcord_prod\n"
            "    pool_size: 10\n\n"
            "redis:\n"
            "  url: redis://cache.internal:6379/0\n"
            "  max_connections: 50\n"
            "  ttl: 3600\n\n"
            "logging:\n"
            "  level: INFO\n"
            "  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'\n"
            "  handlers:\n"
            "    - type: console\n"
            "      colorize: true\n"
            "    - type: file\n"
            "      path: /var/log/memcord/app.log\n"
            "      max_size: 100MB\n"
            "      backup_count: 5\n\n"
            "features:\n"
            "  enable_caching: true\n"
            "  enable_compression: true\n"
            "  enable_search: true\n"
            "  max_slot_size: 10MB\n"
            "  description: |\n"
            "    This is a multi-line string in YAML.\n"
            "    It preserves newlines and is used for\n"
            "    longer configuration descriptions.\n\n"
            "# Anchor reference\n"
            "deploy:\n"
            "  version: *version\n"
            "  strategy: rolling\n"
            "  replicas: 3\n"
            "  health_check:\n"
            "    path: /health\n"
            "    interval: 10s\n"
            "    timeout: 5s\n"
        ),
    ),
    # 8. Very long sentences (200+ word paragraph)
    (
        "very_long_sentences",
        (
            "The comprehensive architectural review of the entire distributed system "
            "infrastructure revealed that the primary bottleneck in our data processing "
            "pipeline was located in the transformation layer where incoming raw data "
            "from multiple heterogeneous sources including REST APIs and WebSocket "
            "connections and message queues and file uploads and database change streams "
            "was being serialized into a common internal format before being dispatched "
            "to the appropriate downstream processing units which themselves were "
            "struggling with memory allocation issues caused by the excessive creation "
            "of temporary objects during the parsing phase and the lack of proper "
            "connection pooling in the database access layer and the absence of "
            "circuit breakers in the external service communication modules and "
            "the inefficient caching strategy that was evicting frequently accessed "
            "entries due to a misconfigured LRU cache size parameter that had been "
            "set to only 256 entries instead of the recommended 4096 entries for "
            "our workload profile which typically involves thousands of concurrent "
            "requests per second each requiring access to shared configuration data "
            "and user session information and feature flag state and rate limiting "
            "counters all of which were being fetched from the database on every "
            "single request instead of being cached appropriately. "
            "After thorough analysis, the team decided to implement a multi-tier "
            "caching strategy with local in-memory caches at the application level "
            "backed by a distributed Redis cluster for shared state, combined with "
            "proper connection pooling, circuit breakers, and retry mechanisms with "
            "exponential backoff for all external service calls, which resulted in "
            "a 73% reduction in average response latency and a 91% reduction in "
            "P99 tail latencies during peak traffic periods."
        ),
    ),
    # 9. Many short sentences
    (
        "many_short_sentences",
        (
            "Start here. Go left. Turn right. Stop now. Look up. Check this. "
            "Run fast. Walk slow. Open door. Close window. Read book. Write code. "
            "Fix bug. Ship feature. Test more. Deploy fast. Monitor well. Alert team. "
            "Scale up. Scale down. Roll back. Try again. Push hard. Pull request. "
            "Code review. Merge branch. Tag release. Update docs. Clean cache. "
            "Reset state. Load data. Save file. Parse JSON. Build image. Run tests. "
            "Check logs. Debug issue. Trace error. Find root cause. Apply patch. "
            "Verify fix. Release hotfix. Notify users. Update status. Close ticket. "
            "Plan sprint. Groom backlog. Set priority. Assign task. Track progress. "
            "Report status. Review metrics. Optimize query. Index table. Tune config. "
            "Restart service. Rotate secrets. Backup data. Restore backup."
        ),
    ),
    # 10. Redundant / repetitive content (tests MMR diversity)
    (
        "redundant_content",
        (
            "The caching system improves performance significantly. "
            "Performance is significantly improved by the caching system. "
            "Our caching mechanism provides significant performance improvements. "
            "Significant performance gains come from our caching approach. "
            "The cache implementation makes performance much better. "
            "Better performance results from implementing the cache. "
            "We see significant performance boosts from caching. "
            "Caching provides a notable improvement in system performance. "
            "System performance sees notable improvements through caching. "
            "The performance of the system is boosted by the cache layer. "
            "However, the database optimization also plays a critical role. "
            "Database query optimization reduced latency by 40%. "
            "The memory management system prevents out-of-memory errors. "
            "Error handling was improved across all service boundaries. "
            "Monitoring and alerting ensure issues are caught early."
        ),
    ),
    # 11. Tab / whitespace heavy
    (
        "tab_whitespace_heavy",
        (
            "class Config:\n"
            "\tdef __init__(self):\n"
            "\t\tself.settings = {\n"
            "\t\t\t'database': {\n"
            "\t\t\t\t'host': 'localhost',\n"
            "\t\t\t\t'port': 5432,\n"
            "\t\t\t\t'name': 'mydb',\n"
            "\t\t\t\t'options': {\n"
            "\t\t\t\t\t'pool_size': 10,\n"
            "\t\t\t\t\t'timeout': 30,\n"
            "\t\t\t\t\t'retry': True,\n"
            "\t\t\t\t}\n"
            "\t\t\t},\n"
            "\t\t\t'cache': {\n"
            "\t\t\t\t'backend': 'redis',\n"
            "\t\t\t\t'url': 'redis://localhost:6379',\n"
            "\t\t\t}\n"
            "\t\t}\n\n"
            "    # Mixed indentation below (spaces)\n"
            "    def get_setting(self, path):\n"
            "        keys = path.split('.')\n"
            "        value = self.settings\n"
            "        for key in keys:\n"
            "            value = value[key]\n"
            "        return value\n\n"
            "\t# Back to tabs\n"
            "\tdef update_setting(self, path, new_value):\n"
            "\t\tkeys = path.split('.')\n"
            "\t\tcurrent = self.settings\n"
            "\t\tfor key in keys[:-1]:\n"
            "\t\t\tcurrent = current[key]\n"
            "\t\tcurrent[keys[-1]] = new_value\n\n"
            "The above code shows mixed indentation styles. "
            "Tab-based indentation is used in __init__ and update_setting. "
            "Space-based indentation is used in get_setting. "
            "This mixed style is common in legacy codebases. "
            "Modern Python style guides recommend 4 spaces consistently. "
            "Linters like ruff and flake8 catch these inconsistencies."
        ),
    ),
    # 12. URLs, emails, file paths
    (
        "urls_emails_paths",
        (
            "Project resources and contacts:\n\n"
            "Documentation: https://docs.example.com/v2/getting-started?lang=en&format=html\n"
            "API Endpoint: https://api.example.com/v1/users?page=1&limit=20#results\n"
            "Repository: https://github.com/org/repo/blob/main/src/index.ts\n"
            "Issue tracker: https://jira.example.com/browse/PROJ-1234\n"
            "CI/CD: https://circleci.com/gh/org/repo/tree/main\n\n"
            "Contact the team:\n"
            "- Lead developer: alice@example.com\n"
            "- DevOps engineer: bob.smith@company.org\n"
            "- Support: support+urgent@help.example.co.uk\n"
            "- Security: security-team@example.com\n\n"
            "Important file paths:\n"
            "- Config: C:\\Users\\dev\\AppData\\Local\\myapp\\config.json\n"
            "- Logs: C:\\ProgramData\\myapp\\logs\\app.log\n"
            "- Unix config: /etc/myapp/config.yaml\n"
            "- Unix logs: /var/log/myapp/error.log\n"
            "- Shared drive: \\\\server\\share\\projects\\current\\\n"
            "- Relative: ./src/components/Dashboard.tsx\n"
            "- Home dir: ~/Documents/projects/memcord/\n\n"
            "FTP: ftp://files.example.com/public/releases/\n"
            "SSH: ssh://git@github.com:22/org/repo.git\n"
            "Data URI: data:text/plain;base64,SGVsbG8gV29ybGQ=\n\n"
            "All these paths and URLs must be preserved exactly in storage."
        ),
    ),
    # 13. Numbered & bullet lists (deeply nested)
    (
        "nested_lists",
        (
            "# Release Checklist\n\n"
            "1. Pre-release tasks\n"
            "   1.1. Code freeze\n"
            "      1.1.1. Merge all approved PRs\n"
            "      1.1.2. Lock the main branch\n"
            "      1.1.3. Create release branch\n"
            "   1.2. Testing\n"
            "      1.2.1. Unit tests must pass\n"
            "      1.2.2. Integration tests\n"
            "         - API contract tests\n"
            "         - Database migration tests\n"
            "         - Cache invalidation tests\n"
            "      1.2.3. Performance tests\n"
            "         * Load testing with k6\n"
            "         * Stress testing under 2x peak\n"
            "         * Soak testing for 24 hours\n"
            "   1.3. Documentation\n"
            "      - Update CHANGELOG.md\n"
            "      - Update API docs\n"
            "      - Review migration guide\n\n"
            "2. Release tasks\n"
            "   2.1. Build artifacts\n"
            "      a) Docker images\n"
            "      b) Python packages\n"
            "      c) Documentation site\n"
            "   2.2. Deploy to staging\n"
            "      - Run smoke tests\n"
            "      - Verify monitoring\n"
            "   2.3. Deploy to production\n"
            "      - Blue/green deployment\n"
            "      - Canary rollout (10% -> 50% -> 100%)\n"
            "      - Monitor error rates\n\n"
            "3. Post-release tasks\n"
            "   - Send release announcement\n"
            "   - Update status page\n"
            "   - Archive sprint board\n"
            "   - Plan retrospective\n"
        ),
    ),
    # 14. ALL CAPS text
    (
        "all_caps_text",
        (
            "URGENT: PRODUCTION INCIDENT REPORT\n\n"
            "SEVERITY: P1 - CRITICAL\n"
            "STATUS: RESOLVED\n"
            "DURATION: 2 HOURS 15 MINUTES\n\n"
            "SUMMARY: THE PRIMARY DATABASE CLUSTER EXPERIENCED A COMPLETE OUTAGE "
            "DUE TO A DISK SPACE EXHAUSTION EVENT ON ALL THREE NODES SIMULTANEOUSLY. "
            "THIS CAUSED ALL WRITE OPERATIONS TO FAIL AND READ OPERATIONS TO TIMEOUT "
            "AFTER 30 SECONDS.\n\n"
            "ROOT CAUSE: AN AUTOMATED BACKUP PROCESS WAS MISCONFIGURED AND STORED "
            "BACKUP FILES ON THE SAME VOLUME AS THE DATABASE DATA DIRECTORY. "
            "THE BACKUP RETENTION POLICY WAS SET TO 90 DAYS INSTEAD OF 7 DAYS, "
            "CAUSING ACCUMULATED BACKUP FILES TO CONSUME ALL AVAILABLE DISK SPACE.\n\n"
            "IMPACT: APPROXIMATELY 15,000 USERS WERE UNABLE TO ACCESS THE APPLICATION "
            "DURING THE OUTAGE WINDOW. AN ESTIMATED 2,500 TRANSACTIONS FAILED AND "
            "REQUIRED MANUAL RECONCILIATION.\n\n"
            "RESOLUTION: THE BACKUP DIRECTORY WAS MOVED TO A SEPARATE VOLUME, "
            "OLD BACKUP FILES WERE PURGED, AND THE RETENTION POLICY WAS CORRECTED. "
            "DATABASE SERVICES WERE RESTORED AND ALL FAILED TRANSACTIONS WERE "
            "REPROCESSED.\n\n"
            "ACTION ITEMS:\n"
            "1. IMPLEMENT DISK SPACE MONITORING ALERTS AT 80% AND 90% THRESHOLDS\n"
            "2. SEPARATE BACKUP STORAGE FROM DATA VOLUMES\n"
            "3. ADD AUTOMATED TESTING FOR BACKUP CONFIGURATIONS\n"
            "4. UPDATE RUNBOOK WITH DISK SPACE RECOVERY PROCEDURES"
        ),
    ),
    # 15. Special characters
    (
        "special_characters",
        (
            "Special character stress test for the storage pipeline:\n\n"
            "Brackets and braces: { } [ ] ( ) < > « »\n"
            "Quotes: \" ' ` ' ' " " ‹ ›\n"
            "Math operators: + - × ÷ = ≠ ≈ ≤ ≥ ± ∞ √ ∑ ∏ ∫\n"
            "Logic: ∧ ∨ ¬ ⊕ ∀ ∃ ⊂ ⊃ ∈ ∉ ∪ ∩\n"
            "Arrows: → ← ↑ ↓ ↔ ⇒ ⇐ ⇑ ⇓ ⇔\n"
            "Currency: $ € £ ¥ ₹ ₩ ₽ ₿ ¢\n"
            "Punctuation: ! @ # $ % ^ & * ( ) _ + - = ~ `\n"
            "Separators: | \\ / : ; . , ? !\n"
            "Dashes: - – — ―\n"
            "Dots: . .. ... · • ‥\n"
            "Misc: © ® ™ § ¶ † ‡ ° ′ ″ ‰ ‱\n"
            "Box drawing: ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ─ │\n"
            "Backslash sequences in text: C:\\path\\to\\file, \\n, \\t, \\r, \\\\\n\n"
            "Regex-like patterns: ^start$ .* [a-z]+ \\d{3}-\\d{4} (?:group)\n\n"
            "These characters must survive the full round trip through "
            "summarization, JSON serialization, disk storage, and deserialization "
            "without any corruption or escaping issues."
        ),
    ),
    # 16. Math / scientific
    (
        "math_scientific",
        (
            "Research Notes: Computational Chemistry Simulation Results\n\n"
            "Experiment parameters:\n"
            "- Temperature: 298.15 K (25°C)\n"
            "- Pressure: 1.01325 × 10⁵ Pa (1 atm)\n"
            "- Concentration: 0.1 mol/L (100 mM)\n"
            "- pH: 7.4 ± 0.1\n\n"
            "Key results:\n"
            "- Binding energy: ΔG = -8.3 kcal/mol\n"
            "- Dissociation constant: Kd = 2.5 × 10⁻⁹ M (2.5 nM)\n"
            "- Rate constant: k₁ = 1.2 × 10⁶ M⁻¹s⁻¹\n"
            "- Half-life: t½ = 4.7 hours\n"
            "- Activation energy: Ea = 15.2 kJ/mol\n\n"
            "Chemical formulas:\n"
            "- Water: H₂O\n"
            "- Glucose: C₆H₁₂O₆\n"
            "- ATP: C₁₀H₁₆N₅O₁₃P₃\n"
            "- Ethanol: CH₃CH₂OH\n\n"
            "Statistical analysis:\n"
            "- Sample size: n = 1000\n"
            "- Mean: μ = 3.14159\n"
            "- Standard deviation: σ = 0.00265\n"
            "- Confidence interval (95%): [3.13630, 3.14688]\n"
            "- p-value: 1.5e-5 (highly significant)\n"
            "- R² = 0.9987\n"
            "- χ² = 12.34 (df = 8, p > 0.05)\n\n"
            "Equations:\n"
            "- Einstein: E = mc²\n"
            "- Schrödinger: iℏ∂ψ/∂t = Ĥψ\n"
            "- Boltzmann: S = kB ln Ω\n"
            "- Navier-Stokes: ρ(∂v/∂t + v·∇v) = -∇p + μ∇²v + f\n\n"
            "All numerical values and scientific notation must be preserved exactly."
        ),
    ),
    # 17. Log output
    (
        "log_output",
        (
            "2025-01-15 14:30:00.123 [INFO]  server.startup - Server starting on port 8080\n"
            "2025-01-15 14:30:00.456 [INFO]  db.pool - Connection pool initialized (size=20)\n"
            "2025-01-15 14:30:00.789 [INFO]  cache.redis - Connected to redis://localhost:6379\n"
            "2025-01-15 14:30:01.012 [INFO]  server.ready - Server ready, accepting connections\n"
            "2025-01-15 14:30:05.234 [DEBUG] request.in - GET /api/v1/health -> 200 (2ms)\n"
            "2025-01-15 14:30:10.567 [INFO]  request.in - POST /api/v1/users -> 201 (45ms)\n"
            "2025-01-15 14:30:15.890 [WARN]  cache.miss - Cache miss for key: user:1234:profile\n"
            "2025-01-15 14:30:16.123 [WARN]  db.slow - Slow query detected (230ms): SELECT * FROM...\n"
            "2025-01-15 14:30:20.456 [ERROR] request.fail - POST /api/v1/orders -> 500 (1200ms)\n"
            "2025-01-15 14:30:20.457 [ERROR] order.service - OrderService.create failed: "
            "InsufficientInventoryError: Item SKU-789 has 0 units available\n"
            "2025-01-15 14:30:25.789 [INFO]  metrics.flush - Flushed 150 metrics to Datadog\n"
            "2025-01-15 14:30:30.012 [WARN]  memory.pressure - Heap usage at 78% (1.56GB/2.0GB)\n"
            "2025-01-15 14:30:35.345 [ERROR] circuit.open - Circuit breaker OPEN for PaymentService "
            "(5 failures in 60s, threshold: 3)\n"
            "2025-01-15 14:30:40.678 [INFO]  circuit.half - Circuit breaker HALF-OPEN for "
            "PaymentService, testing recovery\n"
            "2025-01-15 14:30:45.901 [INFO]  circuit.close - Circuit breaker CLOSED for "
            "PaymentService, service recovered\n"
            "2025-01-15 14:31:00.000 [INFO]  gc.stats - GC pause: 12ms (generation 2, "
            "collected 1,234 objects)\n"
        ),
    ),
    # 18. Stack trace
    (
        "stack_trace",
        (
            "Application crashed with the following traceback:\n\n"
            "Traceback (most recent call last):\n"
            '  File "/app/src/server.py", line 142, in handle_request\n'
            "    response = await self.process_request(request)\n"
            '  File "/app/src/server.py", line 198, in process_request\n'
            "    result = await handler(request.body)\n"
            '  File "/app/src/handlers/order.py", line 67, in create_order\n'
            "    order = await self.order_service.create(order_data)\n"
            '  File "/app/src/services/order.py", line 45, in create\n'
            "    inventory = await self.inventory_client.check(items)\n"
            '  File "/app/src/clients/inventory.py", line 23, in check\n'
            "    response = await self.session.post(url, json=payload)\n"
            '  File "/usr/lib/python3.12/aiohttp/client.py", line 500, in _request\n'
            "    raise ClientConnectorError(req.connection_key, exc)\n"
            "aiohttp.ClientConnectorError: Cannot connect to host "
            "inventory-service:8080 ssl:default [Connect call failed "
            "('10.0.5.23', 8080)]\n\n"
            "The above exception was the direct cause of the following exception:\n\n"
            "Traceback (most recent call last):\n"
            '  File "/app/src/handlers/order.py", line 70, in create_order\n'
            "    raise OrderCreationError(f\"Inventory check failed: {e}\")\n"
            "services.exceptions.OrderCreationError: Inventory check failed: "
            "Cannot connect to host inventory-service:8080\n\n"
            "--- JavaScript Error (frontend) ---\n"
            "TypeError: Cannot read properties of undefined (reading 'map')\n"
            "    at OrderList (webpack:///./src/components/OrderList.tsx:45:23)\n"
            "    at renderWithHooks (webpack:///./node_modules/react-dom/...)\n"
            "    at mountIndeterminateComponent (webpack:///./node_modules/...)\n"
            "    at beginWork (webpack:///./node_modules/react-dom/...)\n"
            "    at performUnitOfWork (webpack:///./node_modules/react-dom/...)\n\n"
            "Both errors indicate the inventory service was unreachable, causing "
            "a cascading failure from backend to frontend."
        ),
    ),
    # 19. Mixed punctuation
    (
        "mixed_punctuation",
        (
            "Well... this is interesting — isn't it? The system (version 2.4.1) "
            "performed better than expected; however, some edge cases remain. "
            "Consider the following: (a) latency spikes, (b) memory pressure, "
            "and (c) disk I/O bottlenecks.\n\n"
            '"Is this really the best approach?" asked the reviewer. '
            "'Perhaps,' replied the author, 'but it works — and that's what matters.'\n\n"
            "Key findings:\n"
            "- Response time: 50ms (p50), 120ms (p95), 500ms (p99)...\n"
            "- Error rate: 0.01% — well below the 0.1% SLA threshold\n"
            "- Throughput: 10,000 req/s; peak: 15,000 req/s (!!)\n\n"
            "Note: the em-dash (—) is preferred over the en-dash (–) for "
            "parenthetical expressions; semicolons (;) join related clauses. "
            "Ellipsis (...) indicates trailing thoughts... or omissions.\n\n"
            "Status update [2025-01-15]: \"All systems operational.\" "
            "(Source: https://status.example.com)\n\n"
            "TODO: review the {config} settings — specifically the [timeout] "
            "and (retry) parameters. Also check: "
            "a) rate-limits, b) circuit-breakers, c) fallback-strategies.\n\n"
            "P.S. Don't forget to update the FAQ section (Q&A format). "
            "The team's consensus? Ship it! ...after one more review cycle."
        ),
    ),
    # 20. Extremely long mixed content (5000+ chars)
    (
        "extremely_long_mixed",
        (
            "# Comprehensive System Design Document\n\n"
            "## 1. Introduction\n"
            "This document outlines the complete system design for the next-generation "
            "data processing platform. The platform handles real-time data ingestion, "
            "transformation, storage, and querying across multiple data centers.\n\n"
            "## 2. Architecture Overview\n"
            "The system follows a microservices architecture with event-driven "
            "communication. Key components include:\n\n"
            "### 2.1 Data Ingestion Layer\n"
            "```python\n"
            "class DataIngester:\n"
            "    def __init__(self, config):\n"
            "        self.kafka = KafkaConsumer(config.brokers)\n"
            "        self.buffer = CircularBuffer(size=10000)\n\n"
            "    async def consume(self):\n"
            "        async for message in self.kafka:\n"
            "            validated = self.validate(message)\n"
            "            self.buffer.append(validated)\n"
            "            if self.buffer.is_full():\n"
            "                await self.flush()\n"
            "```\n\n"
            "The ingestion layer processes 50,000 events/second with < 10ms latency. "
            "Events are validated, deduplicated, and buffered before downstream "
            "processing. Invalid events are routed to a dead letter queue.\n\n"
            "### 2.2 Processing Pipeline\n"
            "Events flow through a series of transformation stages:\n"
            "1. **Parsing** — Extract fields from raw payloads\n"
            "2. **Enrichment** — Add metadata from lookup tables\n"
            "3. **Aggregation** — Compute running statistics\n"
            "4. **Routing** — Direct to appropriate storage tier\n\n"
            "Performance metrics:\n"
            "- Throughput: 50K events/s (sustained), 100K events/s (burst)\n"
            "- Latency: p50=5ms, p95=25ms, p99=100ms\n"
            "- Error rate: < 0.001%\n\n"
            "### 2.3 Storage Architecture\n\n"
            "| Tier | Technology | Use Case | Retention |\n"
            "|------|-----------|----------|-----------|\n"
            "| Hot | Redis | Real-time queries | 24 hours |\n"
            "| Warm | PostgreSQL | Recent data | 90 days |\n"
            "| Cold | S3 + Parquet | Historical archive | 7 years |\n\n"
            "Data lifecycle:\n"
            "```\n"
            "Event → Redis (hot) → PostgreSQL (warm) → S3 (cold) → Glacier (archive)\n"
            "  ↑         ↓              ↓                ↓\n"
            "  └── Realtime API    REST API         Batch queries\n"
            "```\n\n"
            "### 2.4 Query Engine\n"
            "The query engine supports multiple access patterns:\n"
            "- Point lookups by ID (< 1ms via Redis)\n"
            "- Range queries by timestamp (< 50ms via PostgreSQL)\n"
            "- Analytical queries (< 30s via Parquet/Athena)\n"
            "- Full-text search (< 100ms via Elasticsearch)\n\n"
            "```sql\n"
            "-- Example analytical query\n"
            "SELECT date_trunc('hour', event_time) AS hour,\n"
            "       event_type,\n"
            "       COUNT(*) AS event_count,\n"
            "       AVG(duration_ms) AS avg_duration,\n"
            "       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99\n"
            "FROM events\n"
            "WHERE event_time >= NOW() - INTERVAL '7 days'\n"
            "GROUP BY 1, 2\n"
            "ORDER BY hour DESC, event_count DESC;\n"
            "```\n\n"
            "## 3. Reliability\n\n"
            "### 3.1 Fault Tolerance\n"
            "The system is designed for 99.99% availability:\n"
            "- All services run in active-active configuration across 3 AZs\n"
            "- Circuit breakers prevent cascading failures\n"
            "- Automatic failover with < 30s recovery time\n"
            "- Data replication factor of 3 for all critical stores\n\n"
            "### 3.2 Disaster Recovery\n"
            "- RPO (Recovery Point Objective): < 1 minute\n"
            "- RTO (Recovery Time Objective): < 15 minutes\n"
            "- Cross-region replication for all persistent data\n"
            "- Automated runbooks for common failure scenarios\n\n"
            "## 4. Security\n"
            "Security measures include:\n"
            "- mTLS for all service-to-service communication\n"
            "- OAuth 2.0 + OIDC for user authentication\n"
            "- Role-based access control (RBAC) with fine-grained permissions\n"
            "- Data encryption at rest (AES-256) and in transit (TLS 1.3)\n"
            "- Audit logging for all data access operations\n"
            "- Regular penetration testing and vulnerability scanning\n\n"
            "## 5. Observability\n"
            "```yaml\n"
            "monitoring:\n"
            "  metrics:\n"
            "    provider: prometheus\n"
            "    scrape_interval: 15s\n"
            "    retention: 30d\n"
            "  logging:\n"
            "    provider: elasticsearch\n"
            "    format: json\n"
            "    retention: 90d\n"
            "  tracing:\n"
            "    provider: jaeger\n"
            "    sample_rate: 0.01\n"
            "    retention: 7d\n"
            "```\n\n"
            "Dashboard alerts:\n"
            "- 🔴 CRITICAL: Error rate > 1% for 5 minutes\n"
            "- 🟡 WARNING: P99 latency > 500ms for 10 minutes\n"
            "- 🟢 INFO: Deployment completed successfully\n\n"
            "## 6. Cost Optimization\n"
            "Monthly estimated costs (USD):\n"
            "- Compute: $12,500 (EKS + EC2)\n"
            "- Storage: $3,200 (S3 + EBS + RDS)\n"
            "- Networking: $1,800 (NAT + data transfer)\n"
            "- Monitoring: $900 (Datadog + PagerDuty)\n"
            "- Total: ~$18,400/month\n\n"
            "---\n"
            "Document version: 2.1 | Last updated: 2025-01-15 | "
            "Approved by: Architecture Review Board"
        ),
    ),
]

TEXT_BLOCK_IDS = [name for name, _ in TEXT_BLOCKS]
TEXT_BLOCK_VALUES = [text for _, text in TEXT_BLOCKS]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def summarizer():
    return TextSummarizer()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


# ---------------------------------------------------------------------------
# PRE tests — summarizer output quality
# ---------------------------------------------------------------------------


class TestPreSummarizer:
    """PRE tests: verify the summarizer handles all content types correctly."""

    @pytest.mark.parametrize("text_block", TEXT_BLOCK_VALUES, ids=TEXT_BLOCK_IDS)
    def test_no_crash(self, summarizer, text_block):
        """Summarizer handles all content types without crashing."""
        result = summarizer.summarize(text_block)
        assert result is not None

    @pytest.mark.parametrize("text_block", TEXT_BLOCK_VALUES, ids=TEXT_BLOCK_IDS)
    def test_summary_is_string_and_nonempty(self, summarizer, text_block):
        """Summary is always a non-empty string."""
        result = summarizer.summarize(text_block)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("text_block", TEXT_BLOCK_VALUES, ids=TEXT_BLOCK_IDS)
    def test_summary_shorter_than_original(self, summarizer, text_block):
        """Summary is shorter than or equal to original.

        The summarizer may pass through very short texts (<=2 sentences)
        unchanged, so we allow summary_len <= original_len.
        """
        result = summarizer.summarize(text_block)
        assert len(result) <= len(text_block)

    @pytest.mark.parametrize("text_block", TEXT_BLOCK_VALUES, ids=TEXT_BLOCK_IDS)
    def test_stats_consistent(self, summarizer, text_block):
        """get_summary_stats returns lengths matching actual strings."""
        summary = summarizer.summarize(text_block)
        stats = summarizer.get_summary_stats(text_block, summary)

        assert stats["original_length"] == len(text_block)
        assert stats["summary_length"] == len(summary)
        assert stats["original_words"] == len(text_block.split())
        assert stats["summary_words"] == len(summary.split())
        # Backward-compat aliases
        assert stats["words_original"] == stats["original_words"]
        assert stats["words_summary"] == stats["summary_words"]
        # Compression ratio
        assert 0.0 <= stats["compression_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# POST tests — storage round-trip integrity
# ---------------------------------------------------------------------------


class TestPostStorage:
    """POST tests: summarize -> store -> read back -> verify integrity."""

    @pytest.mark.parametrize(
        "idx,text_block",
        enumerate(TEXT_BLOCK_VALUES),
        ids=TEXT_BLOCK_IDS,
    )
    async def test_entry_type_and_fields(self, temp_dir, idx, text_block):
        """Stored entry has type=auto_summary and correct length fields."""
        summarizer = TextSummarizer()
        summary = summarizer.summarize(text_block)

        storage = StorageManager(
            memory_dir=temp_dir,
            shared_dir=str(Path(temp_dir) / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        slot_name = f"post_test_{idx}"
        returned_entry = await storage.add_summary_entry(slot_name, text_block, summary)

        # Verify the returned entry
        assert returned_entry.type == "auto_summary"
        assert returned_entry.original_length == len(text_block)
        assert returned_entry.summary_length == len(summary)

        # Read back from disk
        slot = await storage.read_memory(slot_name)
        assert slot is not None
        assert len(slot.entries) == 1

        entry = slot.entries[0]
        assert entry.type == "auto_summary"
        assert entry.original_length == len(text_block)
        assert entry.summary_length == len(summary)

    @pytest.mark.parametrize(
        "idx,text_block",
        enumerate(TEXT_BLOCK_VALUES),
        ids=TEXT_BLOCK_IDS,
    )
    async def test_content_matches_summary(self, temp_dir, idx, text_block):
        """Stored content exactly matches what the summarizer produced."""
        summarizer = TextSummarizer()
        summary = summarizer.summarize(text_block)

        storage = StorageManager(
            memory_dir=temp_dir,
            shared_dir=str(Path(temp_dir) / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        slot_name = f"content_test_{idx}"
        await storage.add_summary_entry(slot_name, text_block, summary)

        # Read back and compare byte-for-byte
        slot = await storage.read_memory(slot_name)
        assert slot is not None
        entry = slot.entries[0]
        assert entry.content == summary, (
            f"Content mismatch for block {idx}!\n"
            f"  Expected len={len(summary)}, got len={len(entry.content)}\n"
            f"  Expected repr (first 200): {summary[:200]!r}\n"
            f"  Got repr     (first 200): {entry.content[:200]!r}"
        )

    @pytest.mark.parametrize(
        "idx,text_block",
        enumerate(TEXT_BLOCK_VALUES),
        ids=TEXT_BLOCK_IDS,
    )
    async def test_searchable(self, temp_dir, idx, text_block):
        """Stored summary is discoverable via search."""
        summarizer = TextSummarizer()
        summary = summarizer.summarize(text_block)

        storage = StorageManager(
            memory_dir=temp_dir,
            shared_dir=str(Path(temp_dir) / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        slot_name = f"search_test_{idx}"
        await storage.add_summary_entry(slot_name, text_block, summary)

        # Pick a search term from the summary (first significant word >=4 chars)
        words = [w.strip(".,;:!?\"'()[]{}") for w in summary.split()]
        search_word = next(
            (w for w in words if len(w) >= 4 and w.isalpha()),
            words[0] if words else "test",
        )

        query = SearchQuery(
            query=search_word,
            content_types=["auto_summary"],
            max_results=10,
            case_sensitive=False,
        )
        results = await storage.search_memory(query)

        # The slot should appear in search results
        matching_slots = [r.slot_name for r in results]
        assert slot_name in matching_slots, (
            f"Block {idx} not found in search results.\n"
            f"  Search word: {search_word!r}\n"
            f"  Summary (first 200): {summary[:200]!r}\n"
            f"  Results: {matching_slots}"
        )
