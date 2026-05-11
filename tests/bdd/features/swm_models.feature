Feature: SWM models — Pydantic data layer for watchdog state

  As the voyager clearance bot
  I want validated Pydantic models that represent SWM poll and thread state
  So that serialization and deserialization are type-safe and auditable

  # ---------------------------------------------------------------------------
  # Status enum
  # ---------------------------------------------------------------------------

  Scenario: Status enum members cover all poll states
    Given the SWM Status enum
    Then the Status enum has members ready,blocked,pending,error,skipped

  # ---------------------------------------------------------------------------
  # Verdict enum
  # ---------------------------------------------------------------------------

  Scenario: Verdict enum has three valid values
    Given the SWM Verdict enum
    Then the Verdict enum has members RESOLVED,OPEN,NEEDS_HUMAN_JUDGMENT

  # ---------------------------------------------------------------------------
  # Severity enum
  # ---------------------------------------------------------------------------

  Scenario: Severity enum has P1, P2, P3
    Given the SWM Severity enum
    Then the Severity enum has members P1,P2,P3

  # ---------------------------------------------------------------------------
  # CIConclusion enum
  # ---------------------------------------------------------------------------

  Scenario: CIConclusion enum has expected values
    Given the SWM CIConclusion enum
    Then the CIConclusion enum has members SUCCESS,FAILURE,IN_PROGRESS,PENDING,SKIPPED,NEUTRAL,CANCELLED

  # ---------------------------------------------------------------------------
  # Thread model
  # ---------------------------------------------------------------------------

  Scenario: Thread model validates required fields
    Given a valid Thread dict with id "PRRT_abc" and severity "P2"
    When the Thread dict is validated
    Then the Thread model is valid with verdict "OPEN"

  Scenario: Thread model accepts extra fields without error
    Given a Thread dict with an extra unknown field
    When the Thread dict is validated
    Then the Thread model is valid with verdict "OPEN"

  # ---------------------------------------------------------------------------
  # PollRecord model
  # ---------------------------------------------------------------------------

  Scenario: PollRecord state_key is stable for identical records
    Given two identical PollRecord instances
    When their state_keys are computed
    Then the state_keys are equal

  Scenario: PollRecord state_key changes when head_sha changes
    Given two PollRecord instances differing only in head_sha
    When their state_keys are computed
    Then the state_keys are not equal

  Scenario: PollRecord state_key changes when codex_open changes
    Given two PollRecord instances differing only in codex_open count
    When their state_keys are computed
    Then the state_keys are not equal

  Scenario: PollRecord round-trips through JSON serialization
    Given a PollRecord with a thread and CI data
    When the PollRecord is serialized and deserialized
    Then the deserialized PollRecord equals the original

  # ---------------------------------------------------------------------------
  # ThreadSnapshot model
  # ---------------------------------------------------------------------------

  Scenario: ThreadSnapshot round-trips through JSON serialization
    Given a ThreadSnapshot with evidence
    When the ThreadSnapshot is serialized and deserialized
    Then the deserialized ThreadSnapshot equals the original

  # ---------------------------------------------------------------------------
  # LedgerEntry model
  # ---------------------------------------------------------------------------

  Scenario: LedgerEntry accepts extra legacy fields
    Given a LedgerEntry JSON with extra legacy fields
    When the LedgerEntry JSON is deserialized
    Then the LedgerEntry action is "submit_review_approve"
    And the extra field is preserved

  # ---------------------------------------------------------------------------
  # BoxMiss model
  # ---------------------------------------------------------------------------

  Scenario: BoxMiss model validates repo and reason
    Given a BoxMiss with repo "owner/repo" and reason "no matching rule"
    When the BoxMiss is validated
    Then the BoxMiss rule_id is None

  Scenario: BoxMiss with a rule_id preserves it
    Given a BoxMiss with repo "owner/repo" and rule_id "ci.ubuntu"
    When the BoxMiss is validated
    Then the BoxMiss rule_id is "ci.ubuntu"
