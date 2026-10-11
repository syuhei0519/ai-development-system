# Synthetic artifact delivery bundle

All sample content is synthetic and public. No real Issue, task identifier, conversation,
private log, personal information or credential is included. Source bytes are UTF-8 with
LF and a final LF. The Markdown exceeds 32 KiB and ends with a truncation sentinel.
The JSON includes numeric 1 and boolean true as distinct types, literal and escaped
characters, and composed/decomposed Unicode that must not be normalized.

`handoff.json` is one fictional Handoff v2.0 research-design record. Its completed
status is part of the synthetic fixture, not real Research success or product acceptance.
`producer-receipt.json` records the separate operational Producer role; Consumer
verification is pending. It adds no enum to the existing Handoff contract.

## Retrieve exact bytes from a fixed commit

Use the immutable DELIVERY_COMMIT returned in the private delivery response.
Do not use the moving branch head as the verification identity. Use a new, empty
working directory; do not overwrite an earlier bundle. No producer workspace is needed.

```bash
DELIVERY_COMMIT=REPLACE_WITH_FIXED_COMMIT_FROM_DELIVERY_RESPONSE
git clone --no-checkout https://github.com/syuhei0519/ai-development-system.git consumer-repository
cd consumer-repository
git cat-file -e "$DELIVERY_COMMIT^{commit}"
BASE=5ca00d89f97ebc597d214fd8f046e4cc98d781fb
test "$(git rev-parse "$DELIVERY_COMMIT^")" = "$BASE"
P=delivery-verification/20261011/synthetic
mkdir -p "$P" scripts contracts
for f in source.md source.json handoff.json producer-receipt.json README.md verify.py manifest.json; do
  git cat-file blob "$DELIVERY_COMMIT:$P/$f" > "$P/$f"
done
for f in scripts/validate_handoff.py contracts/handoff.schema.json requirements-dev.txt; do
  git cat-file blob "$BASE:$f" > "$f"
done
python3 "$P/verify.py"
python3 scripts/validate_handoff.py "$P/handoff.json"
```

The final command requires jsonschema 4.26.0 (see the fixed requirements-dev.txt).
If unavailable, install that requirements file into a disposable virtual environment.
Record any dependency failure separately from byte retrieval. `git cat-file blob`
extracts stored bytes without checkout line-ending/smudge filters. Schema validation
checks shape and local references only. Independent Consumer success requires its
own receipt with the fixed commit, received hashes/sizes, CLI result and sentinels.

## Optional Git blob API route (not yet independently verified)

Obtain each blob OID with `git rev-parse "$DELIVERY_COMMIT:$P/source.md"`.
The GitHub REST endpoint is `GET /repos/syuhei0519/ai-development-system/git/blobs/{oid}`.
Decode the response's base64 content once into a binary file, then compare size/SHA256.
Check for truncation; never use a rendered preview or JSON reserialization as evidence
of original bytes. Existing authorized access only; no new credentials are needed here.

## Integrity and limits

The manifest hashes every other file in this directory, including the verifier and
receipt, but deliberately excludes itself to avoid a cyclic self-hash. The immutable
Git commit fixes the manifest; its own SHA256 is delivered privately with the commit.
The receipt is sealed before push and does not claim remote reflection or Consumer
success. Push/head confirmation is reported separately after publishing.

Fixed Git is the tested delivery candidate. Git blob API is an optional exact-byte
candidate after decoding and hash checks. Inline reformatted text can lose original
whitespace, Unicode or type distinctions and is untested here. Library transfer is
untested here; no claim is made that its previously reported failure has been resolved.
No paid API or new service is used by this bundle. This is not a pricing guarantee.
