# Security Manifest — kanAPI

> **Purpose**: Machine-readable supply chain inventory for AI-assisted security audits.
> Load this file as context when checking for compromised dependencies.
>
> **Last audited**: 2026-03-31
> **Audit method**: Cross-referenced against StepSecurity incidents database, npm advisories, PyPI advisories.
> **Result**: All clean — no compromised packages found.

---

## How to Use This File

When prompted to check for security issues:

1. **Fetch the latest threat intel** from these sources:
   - https://www.stepsecurity.io/incidents — CI/CD supply chain incidents
   - https://www.stepsecurity.io/npm-security — npm-specific compromises
   - `npm audit` output (run in `frontend/`)
   - `uv run pip-audit` or check https://pypi.org/security/ for PyPI advisories
2. **Cross-reference** every package+version below against the compromised versions listed.
3. **Report** any matches with: package name, your version, compromised version, CVE/advisory link, and recommended action.
4. **Check Docker images** against known CVEs via `docker scout` or Trivy.

---

## Docker Images

All images are pinned to exact tags. No floating tags (`latest`, `alpine`) are used.

| Service | Image | Tag | Notes |
|---------|-------|-----|-------|
| App (build) | `python` | `3.13-alpine3.22` | Multi-stage Dockerfile |
| App (production) | `python` | `3.13-alpine3.22` | Multi-stage Dockerfile |
| PostgreSQL (main) | `postgres` | `18.3-alpine3.23` | Main application database |
| PostgreSQL (FGA) | `postgres` | `17.9-alpine3.23` | OpenFGA backend database |
| MinIO | `minio/minio` | `RELEASE.2025-04-22T22-12-26Z` | Object storage (repo archived Feb 2026) |
| OpenFGA (migrate) | `openfga/openfga` | `v1.12.0` | Authorization migration |
| OpenFGA (server) | `openfga/openfga` | `v1.12.0` | Authorization server |
| Nginx | `nginx` | `1.28.3-alpine3.23` | Reverse proxy (stable branch) |

### Docker Warnings

- **MinIO**: The `minio/minio` GitHub repo was archived Feb 2026. No further updates expected. Community fork: `pgsty/minio`. Plan migration when feasible.

---

## Python Dependencies (from uv.lock)

Runtime: Python >=3.11, <3.14 (currently 3.13.12)

### Direct Dependencies

| Package | Locked Version | Category |
|---------|---------------|----------|
| fastapi | 0.135.2 | Web framework |
| uvicorn | 0.42.0 | ASGI server |
| starlette | 1.0.0 | ASGI toolkit (fastapi dep) |
| pydantic | 2.12.5 | Validation |
| pydantic-core | 2.41.5 | Validation (pydantic dep) |
| sqlalchemy | 2.0.48 | ORM |
| psycopg2-binary | 2.9.11 | PostgreSQL driver |
| pyjwt | 2.12.1 | JWT auth |
| bcrypt | 5.0.0 | Password hashing |
| httpx | 0.28.1 | HTTP client |
| requests | 2.33.1 | HTTP client |
| minio | 7.2.20 | S3-compatible storage |
| openfga-sdk | 0.10.0 | Authorization client |
| slowapi | 0.1.9 | Rate limiting |
| python-dotenv | 1.2.2 | Env config |
| python-multipart | 0.0.22 | Form parsing |
| email-validator | 2.3.0 | Email validation |
| faker | 40.12.0 | Test data generation |
| markitdown | 0.1.5 | Document conversion |
| rumdl | 0.1.63 | Markdown linting |
| uuid7 | 0.1.0 | UUID v7 generation |

### Transitive Dependencies

| Package | Locked Version |
|---------|---------------|
| aiohappyeyeballs | 2.6.1 |
| aiohttp | 3.13.4 |
| aiosignal | 1.4.0 |
| annotated-doc | 0.0.4 |
| annotated-types | 0.7.0 |
| anyio | 4.13.0 |
| argon2-cffi | 25.1.0 |
| argon2-cffi-bindings | 25.1.0 |
| attrs | 26.1.0 |
| beautifulsoup4 | 4.14.3 |
| certifi | 2026.2.25 |
| cffi | 2.0.0 |
| charset-normalizer | 3.4.6 |
| click | 8.3.1 |
| colorama | 0.4.6 |
| coloredlogs | 15.0.1 |
| cryptography | 46.0.6 |
| defusedxml | 0.7.1 |
| deprecated | 1.3.1 |
| dnspython | 2.8.0 |
| flatbuffers | 25.12.19 |
| frozenlist | 1.8.0 |
| greenlet | 3.3.2 |
| h11 | 0.16.0 |
| httpcore | 1.0.9 |
| humanfriendly | 10.0 |
| idna | 3.11 |
| importlib-metadata | 8.7.1 |
| iniconfig | 2.3.0 |
| limits | 5.8.0 |
| magika | 0.6.3 |
| markdownify | 1.2.2 |
| mpmath | 1.3.0 |
| multidict | 6.7.1 |
| numpy | 2.4.4 |
| onnxruntime | 1.20.1 |
| opentelemetry-api | 1.40.0 |
| packaging | 26.0 |
| pdfminer-six | 20251230 |
| pdfplumber | 0.11.9 |
| pillow | 12.1.1 |
| pluggy | 1.6.0 |
| propcache | 0.4.1 |
| protobuf | 7.34.1 |
| pycparser | 3.0 |
| pycryptodome | 3.23.0 |
| pygments | 2.20.0 |
| pypdfium2 | 5.6.0 |
| pyreadline3 | 3.5.4 |
| python-dateutil | 2.9.0.post0 |
| six | 1.17.0 |
| soupsieve | 2.8.3 |
| sympy | 1.14.0 |
| typing-extensions | 4.15.0 |
| typing-inspection | 0.4.2 |
| tzdata | 2025.3 |
| urllib3 | 2.6.3 |
| wrapt | 2.1.2 |
| yarl | 1.23.0 |
| zipp | 3.23.0 |

### Dev Dependencies

| Package | Locked Version |
|---------|---------------|
| ruff | 0.15.8 |
| pytest | 9.0.2 |
| pytest-asyncio | 1.3.0 |

---

## Frontend Dependencies (from package-lock.json)

Runtime: Node.js, Vite 7.x, React 19.x

### Direct Dependencies

| Package | Locked Version | Category |
|---------|---------------|----------|
| react | 19.2.4 | UI framework |
| react-dom | 19.2.4 | DOM rendering |
| react-router-dom | 7.13.2 | Routing |

### Direct Dev Dependencies

| Package | Locked Version | Category |
|---------|---------------|----------|
| @eslint/js | 9.39.4 | Linting |
| @types/react | 19.2.14 | TypeScript types |
| @types/react-dom | 19.2.3 | TypeScript types |
| @vitejs/plugin-react | 5.2.0 | Build tooling |
| eslint | 9.39.4 | Linting |
| eslint-plugin-react-hooks | 7.0.1 | Linting |
| eslint-plugin-react-refresh | 0.4.26 | Linting |
| globals | 16.5.0 | Linting |
| vite | 7.3.1 | Build tooling |

### Transitive Dependencies (security-relevant subset)

These are the transitive deps most commonly targeted in supply chain attacks:

| Package | Locked Version | Sept 2025 Compromised Version | Status |
|---------|---------------|-------------------------------|--------|
| chalk | 4.1.2 | 5.6.1 | SAFE (different major) |
| debug | 4.4.3 | 4.4.2 | SAFE (patched version) |
| color-convert | 2.0.1 | 3.1.1 | SAFE (different major) |
| color-name | 1.1.4 | 2.0.1 | SAFE (different major) |
| ansi-styles | 4.3.0 | 6.2.2 | SAFE (different major) |
| supports-color | 7.2.0 | 10.2.1 | SAFE (different major) |
| cross-spawn | 7.0.6 | — | Not compromised |
| semver | 6.3.1 | — | Not compromised |
| postcss | 8.5.8 | — | Not compromised |
| nanoid | 3.3.11 | — | Not compromised |

### All Other Transitive Dependencies

| Package | Version |
|---------|---------|
| @babel/code-frame | 7.29.0 |
| @babel/compat-data | 7.29.0 |
| @babel/core | 7.29.0 |
| @babel/generator | 7.29.1 |
| @babel/helper-compilation-targets | 7.28.6 |
| @babel/helper-globals | 7.28.0 |
| @babel/helper-module-imports | 7.28.6 |
| @babel/helper-module-transforms | 7.28.6 |
| @babel/helper-plugin-utils | 7.28.6 |
| @babel/helper-string-parser | 7.27.1 |
| @babel/helper-validator-identifier | 7.28.5 |
| @babel/helper-validator-option | 7.27.1 |
| @babel/helpers | 7.29.2 |
| @babel/parser | 7.29.2 |
| @babel/plugin-transform-react-jsx-self | 7.27.1 |
| @babel/plugin-transform-react-jsx-source | 7.27.1 |
| @babel/template | 7.28.6 |
| @babel/traverse | 7.29.0 |
| @babel/types | 7.29.0 |
| @eslint-community/eslint-utils | 4.9.1 |
| @eslint-community/regexpp | 4.12.2 |
| @eslint/config-array | 0.21.2 |
| @eslint/config-helpers | 0.4.2 |
| @eslint/core | 0.17.0 |
| @eslint/eslintrc | 3.3.5 |
| @eslint/object-schema | 2.1.7 |
| @eslint/plugin-kit | 0.4.1 |
| @humanfs/core | 0.19.1 |
| @humanfs/node | 0.16.7 |
| @humanwhocodes/module-importer | 1.0.1 |
| @humanwhocodes/retry | 0.4.3 |
| @jridgewell/gen-mapping | 0.3.13 |
| @jridgewell/remapping | 2.3.5 |
| @jridgewell/resolve-uri | 3.1.2 |
| @jridgewell/sourcemap-codec | 1.5.5 |
| @jridgewell/trace-mapping | 0.3.31 |
| @rolldown/pluginutils | 1.0.0-rc.3 |
| @types/babel__core | 7.20.5 |
| @types/babel__generator | 7.27.0 |
| @types/babel__template | 7.4.4 |
| @types/babel__traverse | 7.28.0 |
| @types/estree | 1.0.8 |
| @types/json-schema | 7.0.15 |
| acorn | 8.16.0 |
| acorn-jsx | 5.3.2 |
| ajv | 6.14.0 |
| argparse | 2.0.1 |
| balanced-match | 1.0.2 |
| baseline-browser-mapping | 2.10.13 |
| brace-expansion | 1.1.13 |
| browserslist | 4.28.2 |
| callsites | 3.1.0 |
| caniuse-lite | 1.0.30001782 |
| concat-map | 0.0.1 |
| convert-source-map | 2.0.0 |
| cookie | 1.1.1 |
| cross-spawn | 7.0.6 |
| csstype | 3.2.3 |
| deep-is | 0.1.4 |
| electron-to-chromium | 1.5.329 |
| esbuild | 0.27.4 |
| escalade | 3.2.0 |
| escape-string-regexp | 4.0.0 |
| eslint-scope | 8.4.0 |
| eslint-visitor-keys | 4.2.1 |
| espree | 10.4.0 |
| esquery | 1.7.0 |
| esrecurse | 4.3.0 |
| estraverse | 5.3.0 |
| esutils | 2.0.3 |
| fast-deep-equal | 3.1.3 |
| fast-json-stable-stringify | 2.1.0 |
| fast-levenshtein | 2.0.6 |
| fdir | 6.5.0 |
| file-entry-cache | 8.0.0 |
| find-up | 5.0.0 |
| flat-cache | 4.0.1 |
| flatted | 3.4.2 |
| fsevents | 2.3.3 |
| gensync | 1.0.0-beta.2 |
| glob-parent | 6.0.2 |
| globals | 14.0.0 |
| has-flag | 4.0.0 |
| hermes-estree | 0.25.1 |
| hermes-parser | 0.25.1 |
| ignore | 5.3.2 |
| import-fresh | 3.3.1 |
| imurmurhash | 0.1.4 |
| is-extglob | 2.1.1 |
| is-glob | 4.0.3 |
| isexe | 2.0.0 |
| js-tokens | 4.0.0 |
| js-yaml | 4.1.1 |
| jsesc | 3.1.0 |
| json-buffer | 3.0.1 |
| json-schema-traverse | 0.4.1 |
| json-stable-stringify-without-jsonify | 1.0.1 |
| json5 | 2.2.3 |
| keyv | 4.5.4 |
| levn | 0.4.1 |
| locate-path | 6.0.0 |
| lodash.merge | 4.6.2 |
| lru-cache | 5.1.1 |
| minimatch | 3.1.5 |
| ms | 2.1.3 |
| nanoid | 3.3.11 |
| natural-compare | 1.4.0 |
| node-releases | 2.0.36 |
| optionator | 0.9.4 |
| p-limit | 3.1.0 |
| p-locate | 5.0.0 |
| parent-module | 1.0.1 |
| path-exists | 4.0.0 |
| path-key | 3.1.1 |
| picocolors | 1.1.1 |
| picomatch | 4.0.4 |
| postcss | 8.5.8 |
| prelude-ls | 1.2.1 |
| punycode | 2.3.1 |
| react-refresh | 0.18.0 |
| react-router | 7.13.2 |
| resolve-from | 4.0.0 |
| rollup | 4.60.1 |
| scheduler | 0.27.0 |
| semver | 6.3.1 |
| set-cookie-parser | 2.7.2 |
| shebang-command | 2.0.0 |
| shebang-regex | 3.0.0 |
| source-map-js | 1.2.1 |
| strip-json-comments | 3.1.1 |
| supports-color | 7.2.0 |
| tinyglobby | 0.2.15 |
| type-check | 0.4.0 |
| update-browserslist-db | 1.2.3 |
| uri-js | 4.4.1 |
| which | 2.0.2 |
| word-wrap | 1.2.5 |
| yallist | 3.1.1 |
| yocto-queue | 0.1.0 |
| zod | 4.3.6 |
| zod-validation-error | 4.0.2 |

---

## Known Supply Chain Incidents (Reference)

Incidents tracked as of 2026-03-31. Use this section to quickly check if new advisories affect your versions.

### npm — Sept 2025 Phishing Campaign (chalk/debug/color ecosystem)

Maintainer Josh Junon phished via fake `npmjs.help` domain. Malicious versions contained crypto-wallet-stealing code. Live for ~2 hours before removal.

| Package | Compromised Version | Our Version | Affected? |
|---------|-------------------|-------------|-----------|
| chalk | 5.6.1 | 4.1.2 | No |
| debug | 4.4.2 | 4.4.3 | No |
| strip-ansi | 7.1.1 | not installed | No |
| color-convert | 3.1.1 | 2.0.1 | No |
| color-name | 2.0.1 | 1.1.4 | No |
| ansi-styles | 6.2.2 | 4.3.0 | No |
| ansi-regex | 6.2.1 | not installed | No |
| supports-color | 10.2.1 | 7.2.0 | No |
| wrap-ansi | 9.0.1 | not installed | No |
| color | 5.0.1 | not installed | No |
| color-string | 2.1.1 | not installed | No |
| backslash | 0.2.1 | not installed | No |
| is-arrayish | 0.3.3 | not installed | No |
| error-ex | 1.3.3 | not installed | No |
| slice-ansi | 7.1.1 | not installed | No |
| simple-swizzle | 0.2.3 | not installed | No |
| chalk-template | 1.1.1 | not installed | No |
| supports-hyperlinks | 4.1.1 | not installed | No |

### npm — Aug 2025 Nx Compromise (S1ngularity)

| Package | Compromised Versions | Our Version | Affected? |
|---------|---------------------|-------------|-----------|
| nx | 20.9-20.12, 21.5-21.8 | not installed | No |

### npm — Mar 2026 Axios RAT

| Package | Compromised Versions | Our Version | Affected? |
|---------|---------------------|-------------|-----------|
| axios | 1.14.1, 0.30.4 | not installed | No |

### npm — Feb 2026 Cline Backdoor

| Package | Compromised Version | Our Version | Affected? |
|---------|-------------------|-------------|-----------|
| cline | 2.3.0 | not installed | No |

### npm — Jul 2025 eslint-prettier Phishing

| Package | Compromised Version | Our Version | Affected? |
|---------|-------------------|-------------|-----------|
| eslint-config-prettier | unknown | not installed | No |
| eslint-plugin-prettier | unknown | not installed | No |

### PyPI — Jul 2025 num2words

| Package | Compromised Version | Our Version | Affected? |
|---------|-------------------|-------------|-----------|
| num2words | 0.5.15 | not installed | No |

---

## Threat Intel Sources

Check these when running a security audit:

| Source | URL | Covers |
|--------|-----|--------|
| StepSecurity Incidents | https://www.stepsecurity.io/incidents | CI/CD + npm supply chain |
| StepSecurity npm Security | https://www.stepsecurity.io/npm-security | npm compromises |
| npm Advisories | https://github.com/advisories?query=ecosystem%3Anpm | npm CVEs |
| PyPI Advisories | https://github.com/advisories?query=ecosystem%3Apip | PyPI CVEs |
| Docker Scout | `docker scout cves <image>` | Container CVEs |
| OSV.dev | https://osv.dev/ | Cross-ecosystem vulnerability DB |
| Snyk Vulnerability DB | https://security.snyk.io/ | All ecosystems |
