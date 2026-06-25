## approachWrong signals

Look for code patterns where the first implementation a developer would try is
structurally incorrect - not buggy, but architecturally wrong in a way that
requires backtracking.

| # | Signal | What to look for | Why it implies "approach likely wrong" |
|---|--------|------------------|-----------------------------------------|
| 1 | Shared base class with concrete helpers | An abstract/base type that provides working methods (e.g. BaseAdapter.execute(), a Default trait impl) the obvious approach would re-implement instead of delegating to | The naive dev rewrites what already exists; the correct approach calls through the base |
| 2 | Hidden dispatch / registry pattern | A factory, map, or switch that routes to variant implementations (DriverRegistry, codec_map, HANDLERS: Dict[str, Fn]) | Obvious approach adds a new case inline; correct approach registers in the dispatch table |
| 3 | Lazy / deferred initialization | Objects initialized in a start()/connect()/setup() phase, not the constructor (pool.acquire(), lazy_static!, asyncio.ensure_future) | Obvious approach uses the object at construction time; correct approach respects the lifecycle |
| 4 | Internal caching / memoization layer | Results cached by a key the obvious approach would not know to invalidate (lru_cache, sync.Map, WeakRef caches, useMemo deps) | Obvious approach bypasses or poisons the cache silently |
| 5 | Implicit ordering contract | Operations that must happen in a specific order not enforced by types - middleware chains (app.use()), migration sequences, event-listener priority | Obvious approach inserts at the wrong point in the chain |
| 6 | Cross-package / cross-module wiring | A feature that must modify files in 3+ packages/modules that import each other (pkg/api -> pkg/core -> pkg/storage) | Obvious approach puts everything in one package; correct approach threads through existing layers |
| 7 | Protocol / interface with non-obvious required methods | An interface where most methods have defaults but 1-2 MUST be overridden, or where method interaction matters (io.ReadCloser must be closed; an Iterator must handle end-of-iteration) | Obvious approach implements the visible methods, misses the required-but-hidden one |
| 8 | Builder / fluent API with order-dependent state | A builder where calling methods in the wrong order silently produces wrong output (QueryBuilder.where().join() vs .join().where()) | Obvious approach chains in declaration order; correct order is data-dependent |

Verdict calibration: "likely yes" - 3+ signals present on the target layer.
"unclear" - 1-2 signals, or signals present but shallow. "no" - zero signals;
the layer is a straightforward CRUD/pass-through.

---

## invariant signals

Look for constraints that must hold DURING execution (not just at the end) - a
naive implementation passes all final-value assertions but violates a count,
ordering, or lifecycle rule mid-operation.

| # | Signal | What to look for | Why it implies an invariant exists |
|---|--------|------------------|-------------------------------------|
| 1 | Query/operation count constraint | Comments or tests asserting N+1 avoidance, batch sizes, "exactly 2 queries" patterns (EXPLAIN, a QueryCounter, sql.DB.Stats()) | Naive impl issues one query per item; correct impl batches - final values identical, count differs |
| 2 | Paired lifecycle hooks | open/close, begin/commit, acquire/release, subscribe/unsubscribe, ctx.enter/exit that must stay balanced | Naive impl leaks a resource or double-closes - value assertions pass, resource count is wrong |
| 3 | Ordering guaranteed by insertion | Ordered maps (LinkedHashMap), sorted slices, ORDER BY without an explicit sort - where switching to a set/hashmap silently breaks order | Naive impl uses an unordered collection - values present but wrong sequence |
| 4 | Reference counting / refcount netting | Rc/Arc clone counts, connection-pool checkout/checkin, semaphore acquire/release that must net to zero mid-operation | Naive impl leaks refs - end state looks fine, mid-state has a leak |
| 5 | Derived values recomputed after filtering | Aggregates (count, sum, subtreeSize, isLeaf) that must reflect ONLY the filtered/truncated set, not the original | Naive impl filters items but keeps stale aggregates - values exist but are wrong |
| 6 | Transactional visibility | Data written inside a transaction must be visible to reads within it but invisible outside until commit (BEGIN...COMMIT, @Transactional, scoped task groups) | Naive impl reads outside the transaction scope - gets stale data, no error |
| 7 | Idempotency under retry | Operations guarded by IF NOT EXISTS, dedup keys, or INSERT ... ON CONFLICT - calling twice must not double-apply | Naive impl applies twice - final state looks doubled but no error thrown |
| 8 | Concurrency ordering | Mutex acquisition order (sync.Mutex, threading.Lock, tokio::Mutex), channel send/receive sequence, or select priority | Naive impl acquires locks in wrong order - works in tests, deadlocks under load |
| 9 | Cleanup-on-error path | defer, finally, a Drop impl, or context managers that must run even when the happy path throws | Naive impl only cleans up on success - error path leaks state |

Verdict calibration: "likely yes" - 2+ signals present AND the target layer
touches the constrained resource directly. "unclear" - signals present but the
feature operates at a layer that does not interact with them. "no" - no
lifecycle/count/ordering constraints visible on the target layer.
