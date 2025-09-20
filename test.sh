#!/usr/bin/env bash
set -euo pipefail

# --- Load env file ------------------------------------------------------------
if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
else
  echo "ERROR: .env not found. Copy .env.example to .env and adjust values." >&2
  exit 1
fi

# --- Static test runner settings ----------------------------------------------
SCRIPT="./immich-smart-albums.py"
TIMEOUT_SECS=45
RETRIES=2

# --- Required vars from .env --------------------------------------------------
need() { [[ -n "${!1:-}" ]] || { echo "ERROR: missing required .env var: $1" >&2; exit 1; }; }
need TEST_PERSON1_NAME
need TEST_PERSON2_NAME
need TEST_PERSON3_NAME
need TEST_RARE_UUID
need TEST_INVALID_UUID
need TEST_INVALID_PERSON_NAME

# --- Local aliases for readability --------------------------------------------
P1="$TEST_PERSON1_NAME"
P2="$TEST_PERSON2_NAME"
P3="$TEST_PERSON3_NAME"
RARE_UUID="$TEST_RARE_UUID"
INVALID_UUID="$TEST_INVALID_UUID"
INVALID_NAME="$TEST_INVALID_PERSON_NAME"

count_urls() {
  local -a args=("$@")
  local attempt=0
  local out
  echo ">>> $SCRIPT ${args[*]}" >&2
  while true; do
    if out=$(timeout "$TIMEOUT_SECS" "$SCRIPT" "${args[@]}" 2>/dev/null | awk '/^https?:\/\// {c++} END{print c+0}'); then
      printf '%s\n' "$out"
      return 0
    fi
    attempt=$((attempt+1))
    if [ "$attempt" -gt "$RETRIES" ]; then
      echo "ERROR: command failed after $RETRIES retries: $SCRIPT ${args[*]}" >&2
      return 1
    fi
    echo "WARN: retrying ($attempt/$RETRIES)..." >&2
    sleep 1
  done
}

must_fail_resolve() {
  # Run a command that should fail to resolve a name/UUID; succeed only if it exits non-zero.
  local -a args=("$@")
  echo ">>> (expect fail) $SCRIPT ${args[*]}" >&2
  if timeout "$TIMEOUT_SECS" "$SCRIPT" "${args[@]}" >/dev/null 2>&1; then
    echo "ERROR: command unexpectedly succeeded: $SCRIPT ${args[*]}" >&2
    exit 1
  else
    echo "OK: command failed to resolve as expected."
  fi
}

heading() {
  printf "\n--- %s ---\n" "$1"
}

heading "Test Case 1: Basic Sanity Checks"

c1_1=$(count_urls --include-person-names-union "$P1" "$P1" --exclude-person-names-union "$P1" "$P1")
echo "Union(P1,P1) excl same: $c1_1"
[ "$c1_1" -eq 0 ] || exit 1

c1_2a=$(count_urls --include-person-names-union "$P1")
# Use a resolvable but rare UUID for 'no effect' exclusion (instead of invalid UUID which now errors)
c1_2b=$(count_urls --include-person-names-union "$P1" --exclude-person-names-intersection "$P1" "$RARE_UUID")
echo "Union(P1): $c1_2a"
echo "Union(P1) excl (P1∩RARE): $c1_2b"
[ "$c1_2a" -eq "$c1_2b" ] || exit 1

c1_3=$(count_urls --include-person-names-intersection "$P1" "$RARE_UUID")
echo "Intersection(P1,RARE): $c1_3"
[ "$c1_3" -eq 0 ] || exit 1

heading "Test Case 2: Intersection and Exclusion"

c2_1=$(count_urls --include-person-names-intersection "$P1" "$P2" --exclude-person-names-union "$P3")
c2_2=$(count_urls --include-person-names-intersection "$P1" "$P2" --exclude-person-names-union "$RARE_UUID")
echo "Inter(P1,P2) excl P3: $c2_1"
echo "Inter(P1,P2) excl RARE: $c2_2"
[ "$c2_1" -le "$c2_2" ] || exit 1
[ "$c2_1" -eq "$c2_2" ] && echo "Note: RARE not in that set."

heading "Test Case 3: Union and Exclusion"

c3_1=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-union "$P3")
c3_2=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-union "$RARE_UUID")
echo "Union(P1,P2) excl P3: $c3_1"
echo "Union(P1,P2) excl RARE: $c3_2"
[ "$c3_1" -le "$c3_2" ] || exit 1
[ "$c3_1" -eq "$c3_2" ] && echo "Note: RARE not in that union."

heading "Test Case 4: Multiple Intersections"

c4_1=$(count_urls --include-person-names-intersection "$P1" "$P2" "$P3")
c4_2=$(count_urls --include-person-names-intersection "$P1" "$P2")
echo "Inter(P1,P2,P3): $c4_1"
echo "Inter(P1,P2): $c4_2"
[ "$c4_1" -le "$c4_2" ] || exit 1

heading "Test Case 5: Idempotence & Commutativity"

# Union idempotence: A ∪ A == A
c5_1=$(count_urls --include-person-names-union "$P1")
c5_2=$(count_urls --include-person-names-union "$P1" "$P1")
echo "Union(P1): $c5_1"
echo "Union(P1,P1): $c5_2"
[ "$c5_1" -eq "$c5_2" ] || exit 1

# Intersection idempotence: A ∩ A == A
c5_3=$(count_urls --include-person-names-intersection "$P1")
c5_4=$(count_urls --include-person-names-intersection "$P1" "$P1")
echo "Inter(P1): $c5_3"
echo "Inter(P1,P1): $c5_4"
[ "$c5_3" -eq "$c5_4" ] || exit 1

# Union commutativity: A ∪ B == B ∪ A
c5_5=$(count_urls --include-person-names-union "$P1" "$P2")
c5_6=$(count_urls --include-person-names-union "$P2" "$P1")
echo "Union(P1,P2): $c5_5"
echo "Union(P2,P1): $c5_6"
[ "$c5_5" -eq "$c5_6" ] || exit 1

# Intersection commutativity: A ∩ B == B ∩ A
c5_7=$(count_urls --include-person-names-intersection "$P1" "$P2")
c5_8=$(count_urls --include-person-names-intersection "$P2" "$P1")
echo "Inter(P1,P2): $c5_7"
echo "Inter(P2,P1): $c5_8"
[ "$c5_7" -eq "$c5_8" ] || exit 1

heading "Test Case 6: Monotonicity"

# Union monotonicity: |A ∪ B| >= |A| and >= |B|
c6_1=$(count_urls --include-person-names-union "$P1")
c6_2=$(count_urls --include-person-names-union "$P2")
c6_3=$(count_urls --include-person-names-union "$P1" "$P2")
echo "|P1|: $c6_1, |P2|: $c6_2, |P1∪P2|: $c6_3"
[ "$c6_3" -ge "$c6_1" ] || exit 1
[ "$c6_3" -ge "$c6_2" ] || exit 1

# Intersection monotonicity: |A ∩ B| <= |A| and <= |B|
c6_4=$(count_urls --include-person-names-intersection "$P1" "$P2")
echo "|P1∩P2|: $c6_4"
[ "$c6_4" -le "$c6_1" ] || exit 1
[ "$c6_4" -le "$c6_2" ] || exit 1

# Triple intersection monotonicity: |A∩B∩C| <= |A∩B|
c6_5=$(count_urls --include-person-names-intersection "$P1" "$P2" "$P3")
echo "|P1∩P2∩P3|: $c6_5"
[ "$c6_5" -le "$c6_4" ] || exit 1

heading "Test Case 7: Inclusion–Exclusion (2 sets)"

# |A ∪ B| + |A ∩ B| == |A| + |B|
c7_A=$(count_urls --include-person-names-union "$P1")
c7_B=$(count_urls --include-person-names-union "$P2")
c7_U=$(count_urls --include-person-names-union "$P1" "$P2")
c7_I=$(count_urls --include-person-names-intersection "$P1" "$P2")
echo "|P1|: $c7_A, |P2|: $c7_B, |P1∪P2|: $c7_U, |P1∩P2|: $c7_I"
sum_left=$((c7_U + c7_I))
sum_right=$((c7_A + c7_B))
[ "$sum_left" -eq "$sum_right" ] || { echo "Inclusion–Exclusion failed"; exit 1; }

heading "Test Case 8a: Resolve Failure for Non-Existent UUID"

# This must fail to resolve and return non-zero.
must_fail_resolve --include-person-names-union "$P1" --exclude-person-names-intersection "$P1" "$INVALID_UUID"

heading "Test Case 8b: Resolve Failure for Non-Existent Person Name"

# This must fail to resolve and return non-zero.
must_fail_resolve --include-person-names-union "$P1" "$INVALID_NAME"


heading "Test Case 9: Exclusion Semantics"

# Excluding the rare, resolvable UUID should not change counts (assuming no intersection)
c9_1=$(count_urls --include-person-names-union "$P1" "$P2")
c9_2=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-union "$RARE_UUID")
echo "Union(P1,P2): $c9_1 vs excl RARE: $c9_2"
[ "$c9_1" -eq "$c9_2" ] || exit 1

# Excluding by union is stricter than excluding by intersection on the same names
c9_3=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-intersection "$P1" "$P2")
c9_4=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-union "$P1" "$P2")
echo "Excl (P1∩P2): $c9_3 vs Excl (P1∪P2): $c9_4"
[ "$c9_3" -ge "$c9_4" ] || exit 1

# If you *include* A∩B and *exclude* A∪B, the result must be 0
c9_5=$(count_urls --include-person-names-intersection "$P1" "$P2" --exclude-person-names-union "$P1" "$P2")
echo "Inter(P1,P2) excl Union(P1,P2): $c9_5"
[ "$c9_5" -eq 0 ] || exit 1

# Duplicated excludes don't change results
c9_6=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-union "$P3")
c9_7=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-union "$P3" "$P3")
echo "Excl P3: $c9_6 vs Excl P3,P3: $c9_7"
[ "$c9_6" -eq "$c9_7" ] || exit 1

heading "Test Case 10: Distribution-ish Checks"

c10_1=$(count_urls --include-person-names-union "$P1" "$P2")
c10_2=$(count_urls --include-person-names-union "$P1" "$P2" --exclude-person-names-intersection "$P1" "$P2")
echo "|P1∪P2|: $c10_1 vs (P1∪P2) excl (P1∩P2): $c10_2"
[ "$c10_2" -le "$c10_1" ] || exit 1

heading "Test Case 11: Self-canceling Exclude"

# Include A then exclude A (by union) -> 0
c11_1=$(count_urls --include-person-names-union "$P1" --exclude-person-names-union "$P1")
echo "Include P1 excl P1: $c11_1"
[ "$c11_1" -eq 0 ] || exit 1

# Include A∩B then exclude B (by union) -> 0
c11_2=$(count_urls --include-person-names-intersection "$P1" "$P2" --exclude-person-names-union "$P2")
echo "Include (P1∩P2) excl P2: $c11_2"
[ "$c11_2" -eq 0 ] || exit 1

heading "Test Case 12: UUID Handling (Resolvable, Rare)"

# Idempotence with UUID
c12_1=$(count_urls --include-person-names-union "$RARE_UUID")
c12_2=$(count_urls --include-person-names-union "$RARE_UUID" "$RARE_UUID")
echo "Union(RARE): $c12_1"
echo "Union(RARE,RARE): $c12_2"
[ "$c12_1" -eq "$c12_2" ] || exit 1

# Excluding itself zeroes results
c12_3=$(count_urls --include-person-names-union "$RARE_UUID" --exclude-person-names-union "$RARE_UUID")
echo "Include RARE excl RARE: $c12_3"
[ "$c12_3" -eq 0 ] || exit 1

heading "Test Case 13: Mixed Name and UUID (Resolvable, Rare)"

# Union with RARE_UUID shouldn't reduce counts
c13_1=$(count_urls --include-person-names-union "$P3")
c13_2=$(count_urls --include-person-names-union "$P3" "$RARE_UUID")
echo "Union(P3): $c13_1"
echo "Union(P3, RARE): $c13_2"
[ "$c13_2" -ge "$c13_1" ] || exit 1

# Intersection with RARE should be 0 if there's no overlap; at minimum it's <= |P3|
c13_3=$(count_urls --include-person-names-intersection "$P3" "$RARE_UUID")
echo "Intersection(P3, RARE): $c13_3"
[ "$c13_3" -le "$c13_1" ] || exit 1
# If your sample set guarantees no overlap with RARE, keep the stronger check:
[ "$c13_3" -eq 0 ] || exit 1

heading "Test Case 14: Smart Query Syntax"

# Test that exclusion reduces the count of a query.
# First, count assets with 'dog' AND 'cat'.
c14_1a=$(count_urls --include-smart-intersection "dog" "cat")
# Now, count the same but exclude 'dog'. This should be less than the first count.
c14_1b=$(count_urls --include-smart-intersection "dog" "cat" --exclude-smart-union "dog")
echo "Include ('dog' AND 'cat'): $c14_1a"
echo "Include ('dog' AND 'cat') EXCL 'dog': $c14_1b"
# The second count must be less than the first, unless both are zero.
[ "$c14_1b" -lt "$c14_1a" ] || { [ "$c14_1a" -eq 0 ] && [ "$c14_1b" -eq 0 ]; } || exit 1

# Query with inline limit
c14_2=$(count_urls --include-smart-union "cat @50")
echo "Include with inline limit 'cat @50': $c14_2"
[ "$c14_2" -ge 0 ] || exit 1

# Inline JSON query
c14_3=$(count_urls --include-smart-union '{"query":"car","resultLimit":25}')
echo "Include with inline JSON: $c14_3"
[ "$c14_3" -ge 0 ] || exit 1

# Test that inline limit is respected
c14_4=$(count_urls --include-smart-union "dog @10")
echo "Include with inline limit 'dog @10': $c14_4"
[ "$c14_4" -le 10 ] || exit 1

heading "Test Case 15: Multiple Argument Occurrences"

# 1. Multiple Union Includes
c15_1_single=$(count_urls --include-person-names-union "$P1" "$P2")
c15_1_multiple=$(count_urls --include-person-names-union "$P1" --include-person-names-union "$P2")
echo "Union(P1,P2) single arg: $c15_1_single"
echo "Union(P1,P2) multiple args: $c15_1_multiple"
[ "$c15_1_single" -eq "$c15_1_multiple" ] || { echo "Multiple Union Includes failed"; exit 1; }

# 2. Multiple Intersection Includes
c15_2_single=$(count_urls --include-person-names-intersection "$P1" "$P2" "$P3")
c15_2_multiple=$(count_urls --include-person-names-intersection "$P1" "$P2" --include-person-names-intersection "$P2" "$P3")
echo "Inter(P1,P2,P3) single arg: $c15_2_single"
echo "Inter(P1,P2,P3) multiple args: $c15_2_multiple"
[ "$c15_2_single" -eq "$c15_2_multiple" ] || { echo "Multiple Intersection Includes failed"; exit 1; }

# 3. Multiple Union Excludes
c15_3_single=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-union "$P1" "$P2")
c15_3_multiple=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-union "$P1" --exclude-person-names-union "$P2")
echo "Excl Union(P1,P2) single arg: $c15_3_single"
echo "Excl Union(P1,P2) multiple args: $c15_3_multiple"
[ "$c15_3_single" -eq "$c15_3_multiple" ] || { echo "Multiple Union Excludes failed"; exit 1; }

# 4. Multiple Intersection Excludes
c15_4_single=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-intersection "$P1" "$P2" "$P3")
c15_4_multiple=$(count_urls --include-person-names-union "$P1" "$P2" "$P3" --exclude-person-names-intersection "$P1" "$P2" --exclude-person-names-intersection "$P2" "$P3")
echo "Excl Inter(P1,P2,P3) single arg: $c15_4_single"
echo "Excl Inter(P1,P2,P3) multiple args: $c15_4_multiple"
[ "$c15_4_single" -eq "$c15_4_multiple" ] || { echo "Multiple Intersection Excludes failed"; exit 1; }

echo "Test Case 16: Complex Exclusion of Intersecting Pairs"

c16_AC_excl_pairs=$(count_urls \
  --include-person-names-intersection "$P1" "$P3" \
  --exclude-person-names-intersection "$P1" "$P2" \
  --exclude-person-names-intersection "$P2" "$P3")
echo "|P1 ∩ P3| excl (P1 ∩ P2) and (P2 ∩ P3): $c16_AC_excl_pairs"


# Cross-check 1: Excluding B by UNION equals excluding the two pairs
c16_AC_excl_B_union=$(count_urls \
  --include-person-names-intersection "$P1" "$P3" \
  --exclude-person-names-union "$P2")
echo "|P1 ∩ P3| excl P2 (union): $c16_AC_excl_B_union"
[ "$c16_AC_excl_B_union" -eq "$c16_AC_excl_pairs" ] || { echo "Pair-exclusion vs union(B) mismatch"; exit 1; }

# Cross-check 2: Excluding only the triple intersection equals the pair-exclusion result
c16_AC_excl_ABC=$(count_urls \
  --include-person-names-intersection "$P1" "$P3" \
  --exclude-person-names-intersection "$P1" "$P2" "$P3")
echo "|P1 ∩ P3| excl (P1 ∩ P2 ∩ P3): $c16_AC_excl_ABC"
[ "$c16_AC_excl_ABC" -eq "$c16_AC_excl_pairs" ] || { echo "Excluding only the triple mismatch"; exit 1; }


# ---------------------------

echo
echo "All tests passed!"
