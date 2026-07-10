# Architecture decision record

## Context

The bot combines two Telegram roles: a Telethon user client reads channel posts, while a Bot API client publishes selected notifications. An optional GigaChat adapter refines a local keyword prefilter.

The former single-class implementation coupled configuration, classification, transport, retries, queueing, formatting, metrics and lifecycle. That made external integrations hard to replace and allowed delivery failures to be counted as successful processing.

## Quality attributes

1. **Correct delivery accounting** — a failed or partial send must never be reported as fully delivered.
2. **Duplicate resistance** — failure of one destination/part must not resend already successful parts.
3. **Testability** — application policy must run without Telegram or GigaChat libraries.
4. **Operability** — overload creates backpressure, shutdown drains accepted work and counters describe outcomes.
5. **Simplicity** — one process and SQLite are sufficient; no broker or DI framework is introduced.

## Decision

The project uses a ports-and-adapters boundary:

- `domain.py` owns immutable messages and result types;
- `ports.py` defines the capabilities required by the application layer;
- `application.py` owns filtering/classification/delivery policy;
- `adapters/` owns Telethon, GigaChat and SQLite details;
- `delivery.py` owns Telegram Bot API delivery semantics;
- `runtime.py` and `queueing.py` own process lifecycle and backpressure;
- `main.py` is the only composition root.

## Protected invariants

| Object | Invariant | Enforcement | Verification |
|---|---|---|---|
| Application layer | Does not import concrete network clients | Ports and composition root | `test_architecture.py` |
| Delivery unit | Retry is scoped to `(source_key, chat_id, part_index)` | `TelegramNotificationSink` | delivery regression tests |
| Delivery result | Partial/failed delivery is not success | `DeliveryReport` and `ProcessingOutcome` | application tests |
| Source identity | Deduplication key uses stable Telegram chat id and message id | `IncomingMessage.source_key` | formatting/runtime tests |
| Accepted queue item | Is processed before normal shutdown | `queue.join()` before worker cancellation | runtime drain test |
| Configuration | Invalid booleans and non-positive limits fail fast | typed config parser | config tests |
| AI response | Only exact `ДА/НЕТ` protocol is accepted | `parse_binary_answer` | classification tests |

## Delivery semantics

The bot provides **best-effort at-least-once delivery with durable duplicate suppression**:

1. each destination and Telegram-sized message part is sent independently;
2. a successful unit is recorded in `.runtime/delivery.sqlite3`;
3. recorded units are skipped on ordinary retry or restart;
4. a crash after Telegram accepts a message but before SQLite commits the receipt can still duplicate that unit.

Exactly-once delivery is impossible across the Telegram API and local SQLite without a transactional protocol supported by both systems. Marking a receipt before sending was rejected because it converts a crash into silent message loss.

## Failure policy

GigaChat failures produce `ClassificationDecision.UNAVAILABLE`, not `IRRELEVANT`. The application layer resolves that state using `GIGACHAT_FAIL_OPEN`:

- `True`: send when the local prefilter passed;
- `False`: skip and count `CLASSIFIER_UNAVAILABLE`.

This keeps provider availability separate from the domain decision.

## Rejected alternatives

- **Microservices/message broker** — disproportionate operational cost for a single-worker personal bot.
- **Large DI container** — constructor injection and small protocols are sufficient.
- **One interface per helper function** — would add indirection without protecting a boundary.
- **Global `REQUESTS_CA_BUNDLE`** — replaced by `GIGACHAT_CA_BUNDLE`, scoped to the GigaChat adapter.
- **Silent `put_nowait` drop** — replaced by bounded queue backpressure.

## Extension points

- another classifier implements `MessageClassifier`;
- another output transport implements `NotificationSink`;
- another source implements `MessageSource`;
- formatting changes remain independent of transport;
- delivery persistence can be replaced without changing application policy.
