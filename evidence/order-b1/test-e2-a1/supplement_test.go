// Independent Test supplement for fixed B1 head. Execute via Go overlay; no app edits.
package orderpostgres

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"gitlab.com/platform-engineering-lab/backend-app/internal/account"
	"gitlab.com/platform-engineering-lab/backend-app/internal/httpapi"
	"gitlab.com/platform-engineering-lab/backend-app/internal/order"
	"gitlab.com/platform-engineering-lab/backend-app/internal/orderhttp"
	"gitlab.com/platform-engineering-lab/backend-app/internal/ordertest"
	accountpostgres "gitlab.com/platform-engineering-lab/backend-app/internal/store/postgres"
)

func TestIndependentFreshConcurrencyAndHTTPBoundaries(t *testing.T) {
	d := ordertest.Start(t, "orders", "order_app")
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	stores := make([]*Store, 8)
	for i := range stores {
		s, e := Open(ctx, d.URL())
		if e != nil {
			t.Fatal("open")
		}
		stores[i] = s
		defer s.Close()
	}
	var wg sync.WaitGroup
	errs := make(chan error, 8)
	for _, s := range stores {
		wg.Add(1)
		go func(s *Store) { defer wg.Done(); errs <- s.Migrate(ctx) }(s)
	}
	wg.Wait()
	close(errs)
	for e := range errs {
		if e != nil {
			t.Fatal("fresh concurrent migration failed")
		}
	}
	s := stores[0]
	var history string
	if s.pool.QueryRow(ctx, `SELECT json_agg(h ORDER BY version)::text FROM order_schema_migrations h`).Scan(&history) != nil {
		t.Fatal("history")
	}
	var historyCount int
	if s.pool.QueryRow(ctx, `SELECT count(*) FROM order_schema_migrations WHERE version=1`).Scan(&historyCount) != nil || historyCount != 1 {
		t.Fatal("fresh history not exactly one")
	}
	t.Log("8 independent Store instances concurrently migrated an empty DB; exactly one version-1 row")
	api := httptest.NewServer(orderhttp.New(order.New(s), s))
	defer api.Close()
	client := &http.Client{Timeout: 8 * time.Second}
	count := func() int {
		var n int
		if s.pool.QueryRow(ctx, `SELECT count(*) FROM orders`).Scan(&n) != nil {
			t.Fatal("count")
		}
		return n
	}
	call := func(method, path, body, media string, chunked bool) (int, []byte, http.Header) {
		t.Helper()
		req, e := http.NewRequestWithContext(ctx, method, api.URL+path, strings.NewReader(body))
		if e != nil {
			t.Fatal("request")
		}
		if chunked {
			req.ContentLength = -1
			req.TransferEncoding = []string{"chunked"}
		}
		if media != "" {
			req.Header.Set("Content-Type", media)
		}
		res, e := client.Do(req)
		if e != nil {
			t.Fatal("HTTP request failed")
		}
		defer res.Body.Close()
		raw, e := io.ReadAll(res.Body)
		if e != nil {
			t.Fatal("body")
		}
		return res.StatusCode, raw, res.Header
	}
	valid := `{"account_id":1,"item_code":"A","quantity":1}`
	invalid := []struct {
		name, body, media string
		status            int
	}{
		{"missing-media", valid, "", 415},
		{"latin1", valid, "application/json; charset=iso-8859-1", 415},
		{"unknown-param", valid, "application/json; profile=x", 415},
		{"extra-param", valid, "application/json; charset=utf-8; x=y", 415},
		{"suffix-media", valid, "application/problem+json", 415},
		{"malformed-media", valid, "application/json; charset=", 415},
		{"case-sensitive-key", `{"Account_id":1,"item_code":"A","quantity":1}`, "application/json", 400},
		{"unicode-key-duplicate", `{"account_id":1,"item_code":"A","quantity":1,"\u0071uantity":2}`, "application/json", 400},
		{"unicode-surrogate", `{"account_id":1,"item_code":"\ud800","quantity":1}`, "application/json", 400},
		{"nul-code", `{"account_id":1,"item_code":"A\u0000","quantity":1}`, "application/json", 400},
		{"slash-code", `{"account_id":1,"item_code":"A/B","quantity":1}`, "application/json", 400},
		{"backslash-code", `{"account_id":1,"item_code":"A\\B","quantity":1}`, "application/json", 400},
		{"trailing-newline-code", `{"account_id":1,"item_code":"A\n","quantity":1}`, "application/json", 400},
		{"bom", "\xef\xbb\xbf" + valid, "application/json", 400},
		{"leading-zero", `{"account_id":01,"item_code":"A","quantity":1}`, "application/json", 400},
		{"negative-zero", `{"account_id":1,"item_code":"A","quantity":-0}`, "application/json", 400},
		{"trailing-comment", valid + "/*x*/", "application/json", 400},
		{"extra-comma", `{"account_id":1,"item_code":"A","quantity":1,}`, "application/json", 400},
		{"length-16385", valid + strings.Repeat(" ", 16385-len(valid)), "application/json", 413},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			before := count()
			code, raw, _ := call("POST", "/api/orders", tc.body, tc.media, true)
			if code != tc.status {
				t.Errorf("want %d got %d", tc.status, code)
			}
			if count() != before {
				t.Error("invalid input wrote a row")
			}
			var body struct {
				Error struct{ Code, Message string }
			}
			if json.Unmarshal(raw, &body) != nil || body.Error.Code == "" || body.Error.Message == "" {
				t.Error("error contract")
			}
			if strings.Contains(string(raw), "postgres") {
				t.Error("driver leak")
			}
		})
	}
	for _, body := range []string{valid + strings.Repeat(" ", 16384-len(valid)), `{"quantity":999,"item_code":"Z._-09","\u0061ccount_id":9223372036854775807}`} {
		before := count()
		code, raw, h := call("POST", "/api/orders", body, "Application/JSON; Charset=UTF-8", true)
		if code != 201 || count() != before+1 {
			t.Fatal("valid positive boundary")
		}
		var o order.Order
		if json.Unmarshal(raw, &o) != nil || !strings.HasSuffix(o.CreatedAt.Format(time.RFC3339Nano), "Z") || h.Get("Location") != fmt.Sprintf("/api/orders/%d", o.ID) {
			t.Fatal("representation/UTC/Location")
		}
		code, got, _ := call("GET", h.Get("Location"), "", "", false)
		if code != 200 || string(got) != string(raw) {
			t.Fatal("immediate persisted read")
		}
	}
	for _, method := range []string{"GET", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"} {
		before := count()
		code, _, h := call(method, "/api/orders", valid, "application/json", false)
		if code != 405 || h.Get("Allow") != "POST" || count() != before {
			t.Fatal("collection method boundary")
		}
	}
	// Real concurrent INSERT+commit calls must return distinct IDs, no missing rows.
	before := count()
	ids := make(chan int64, 24)
	ce := make(chan error, 24)
	for i := 0; i < 24; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			o, e := s.Create(ctx, order.Input{AccountID: 1, ItemCode: "Concurrent", Quantity: 1})
			if e != nil {
				ce <- e
				return
			}
			ids <- o.ID
		}()
	}
	wg.Wait()
	close(ids)
	close(ce)
	for e := range ce {
		if e != nil {
			t.Fatal("concurrent create")
		}
	}
	seen := map[int64]bool{}
	for id := range ids {
		if id < 1 || seen[id] {
			t.Fatal("duplicate identity")
		}
		seen[id] = true
	}
	if len(seen) != 24 || count() != before+24 {
		t.Fatal("concurrent row count")
	}
	// Cancellation while waiting for a PostgreSQL table lock: no committed row,
	// connection/transaction resources recover without replacing the Store.
	blocker, e := s.pool.Acquire(ctx)
	if e != nil {
		t.Fatal("blocker")
	}
	tx, e := blocker.Begin(ctx)
	if e != nil {
		t.Fatal("begin blocker")
	}
	if _, e = tx.Exec(ctx, `LOCK TABLE orders IN ACCESS EXCLUSIVE MODE`); e != nil {
		t.Fatal("table lock")
	}
	short, stop := context.WithTimeout(ctx, 150*time.Millisecond)
	_, e = s.Create(short, order.Input{AccountID: 1, ItemCode: "Cancelled", Quantity: 1})
	stop()
	if !errors.Is(e, order.ErrUnavailable) {
		t.Error("cancelled INSERT not unavailable")
	}
	_ = tx.Rollback(ctx)
	blocker.Release()
	if count() != before+24 {
		t.Fatal("cancelled INSERT committed")
	}
	dead, stop := context.WithCancel(ctx)
	stop()
	if _, e = s.Get(dead, 1); !errors.Is(e, order.ErrUnavailable) {
		t.Fatal("cancelled GET")
	}
	for i := 0; i < 12; i++ {
		dead, stop := context.WithCancel(ctx)
		stop()
		if s.Migrate(dead) == nil {
			t.Fatal("cancelled migrate succeeded")
		}
	}
	if s.Migrate(ctx) != nil || s.Ready(ctx) != nil {
		t.Fatal("pool did not recover after cancellation")
	}
	if _, e = s.Create(ctx, order.Input{AccountID: 1, ItemCode: "Recovered", Quantity: 1}); e != nil {
		t.Fatal("create recovery")
	}
	var after string
	s.pool.QueryRow(ctx, `SELECT json_agg(h ORDER BY version)::text FROM order_schema_migrations h`).Scan(&after)
	if after != history {
		t.Fatal("history changed")
	}
	t.Logf("%d extra malformed/media/size chunked cases rejected without writes; 16KiB positive, escaped key, UTC, collection 405, 24 concurrent inserts, cancellation/no-write/recovery passed", len(invalid))
}

func TestIndependentMigrationFailureRollback(t *testing.T) {
	d := ordertest.Start(t, "orders", "order_app")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	s, e := Open(ctx, d.URL())
	if e != nil {
		t.Fatal("open")
	}
	defer s.Close()
	// An existing conflicting table in our own fresh DB causes real embedded SQL failure.
	if _, e = s.pool.Exec(ctx, `CREATE TABLE public.orders(sentinel TEXT); INSERT INTO public.orders VALUES('keep')`); e != nil {
		t.Fatal("fixture")
	}
	if s.Migrate(ctx) == nil {
		t.Fatal("migration unexpectedly succeeded")
	}
	var n int
	var sentinel string
	if s.pool.QueryRow(ctx, `SELECT count(*) FROM order_schema_migrations`).Scan(&n) != nil || n != 0 {
		t.Fatal("failed history persisted")
	}
	if s.pool.QueryRow(ctx, `SELECT sentinel FROM orders`).Scan(&sentinel) != nil || sentinel != "keep" {
		t.Fatal("conflict fixture changed")
	}
	if _, e = s.pool.Exec(ctx, `DROP TABLE orders`); e != nil {
		t.Fatal("own fixture removal")
	}
	if s.Migrate(ctx) != nil || s.Ready(ctx) != nil {
		t.Fatal("forward retry failed")
	}
	// Test transaction atomicity when DDL succeeds but history INSERT fails.
	conn, e := s.pool.Acquire(ctx)
	if e != nil {
		t.Fatal("acquire")
	}
	e = applyMigration(ctx, conn, 1, `CREATE TABLE public.must_rollback(id int)`)
	conn.Release()
	if e == nil {
		t.Fatal("duplicate history accepted")
	}
	var exists bool
	if s.pool.QueryRow(ctx, `SELECT to_regclass('must_rollback') IS NOT NULL`).Scan(&exists) != nil || exists {
		t.Fatal("DDL survived history INSERT failure")
	}
	// Both real connection identity and session cleanup after failure remain valid.
	admin, e := pgxpool.New(ctx, d.AdminURL("orders"))
	if e != nil {
		t.Fatal("admin fixture")
	}
	defer admin.Close()
	if admin.QueryRow(ctx, `SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND granted AND database=(SELECT oid FROM pg_database WHERE datname='orders')`).Scan(&n) != nil || n != 0 {
		t.Fatal("advisory lock leaked")
	}
	t.Log("real embedded migration conflict: nonzero error, unchanged sentinel, zero applied history; clean retry; history failure rolls DDL back; zero leaked advisory locks")
}

func TestIndependentAccountSchemaAndIsolation(t *testing.T) {
	ad := ordertest.Start(t, "accounts", "account_app")
	od := ordertest.Start(t, "orders", "order_app")
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	as, e := accountpostgres.Open(ctx, ad.URL())
	if e != nil {
		t.Fatal("account open")
	}
	defer as.Close()
	if as.Migrate(ctx) != nil {
		t.Fatal("account migrate")
	}
	ap, e := pgxpool.New(ctx, ad.URL())
	if e != nil {
		t.Fatal("account pool")
	}
	defer ap.Close()
	api := httptest.NewServer(httpapi.New(account.New(as), as, slog.New(slog.NewTextHandler(io.Discard, nil))))
	defer api.Close()
	call := func(method, path, body string, want int) []byte {
		t.Helper()
		r, e := http.NewRequestWithContext(ctx, method, api.URL+path, strings.NewReader(body))
		if e != nil {
			t.Fatal("account request")
		}
		r.Header.Set("Content-Type", "application/json")
		res, e := api.Client().Do(r)
		if e != nil {
			t.Fatal("account HTTP")
		}
		defer res.Body.Close()
		b, _ := io.ReadAll(res.Body)
		if res.StatusCode != want {
			t.Fatalf("account status want %d got %d", want, res.StatusCode)
		}
		return b
	}
	sentinelRaw := call("POST", "/api/accounts", `{"name":"Sentinel","email":"sentinel@example.invalid"}`, 201)
	var sentinel account.Account
	if json.Unmarshal(sentinelRaw, &sentinel) != nil {
		t.Fatal("sentinel response")
	}
	snapshot := func() string {
		var raw string
		e := ap.QueryRow(ctx, `SELECT json_build_object(
 'columns',(SELECT json_agg(c ORDER BY table_name,ordinal_position) FROM information_schema.columns c WHERE table_schema='public'),
 'constraints',(SELECT json_agg(c ORDER BY constraint_name) FROM information_schema.table_constraints c WHERE table_schema='public'),
 'indexes',(SELECT json_agg(i ORDER BY indexname) FROM pg_indexes i WHERE schemaname='public'),
 'history',(SELECT json_agg(h ORDER BY version) FROM schema_migrations h),
 'sentinel',(SELECT row_to_json(a) FROM accounts a WHERE id=$1))::text`, sentinel.ID).Scan(&raw)
		if e != nil {
			t.Fatal("schema snapshot")
		}
		return raw
	}
	before := snapshot()
	os, e := Open(ctx, od.URL())
	if e != nil {
		t.Fatal("order open")
	}
	defer os.Close()
	for i := 0; i < 3; i++ {
		if os.Migrate(ctx) != nil {
			t.Fatal("order migration")
		}
	}
	created, e := os.Create(ctx, order.Input{AccountID: sentinel.ID, ItemCode: "Preserved", Quantity: 2})
	if e != nil {
		t.Fatal("order create")
	}
	// Actual migration guard refuses the Account engine even when bypassing Open.
	wrong := &Store{pool: ap}
	if !errors.Is(wrong.Migrate(ctx), ErrTarget) {
		t.Fatal("real Account target not refused")
	}
	if snapshot() != before {
		t.Fatal("Account columns/constraints/indexes/history/sentinel changed")
	}
	raw := call("POST", "/api/accounts", `{"name":"CRUD","email":"crud@example.invalid"}`, 201)
	var fixture account.Account
	if json.Unmarshal(raw, &fixture) != nil {
		t.Fatal("CRUD response")
	}
	path := fmt.Sprintf("/api/accounts/%d", fixture.ID)
	call("GET", "/api/accounts", "", 200)
	call("GET", path, "", 200)
	call("PUT", path, `{"name":"Updated","email":"updated@example.invalid"}`, 200)
	call("DELETE", path, "", 204)
	call("GET", path, "", 404)
	if snapshot() != before || as.Ready(ctx) != nil {
		t.Fatal("Account schema/history/sentinel not preserved after regression")
	}
	call("DELETE", fmt.Sprintf("/api/accounts/%d", sentinel.ID), "", 204)
	got, e := os.Get(ctx, created.ID)
	if e != nil || got.AccountID != sentinel.ID {
		t.Fatal("deleted account removed Order")
	}
	if _, e = os.Create(ctx, order.Input{AccountID: 9223372036854775807, ItemCode: "NoAccount", Quantity: 1}); e != nil {
		t.Fatal("nonexistent account refused")
	}
	var n int
	if os.pool.QueryRow(ctx, `SELECT count(*) FROM pg_constraint WHERE conrelid='orders'::regclass AND contype='f'`).Scan(&n) != nil || n != 0 {
		t.Fatal("unexpected foreign key")
	}
	t.Log("Account columns/constraints/indexes/full history/sentinel unchanged through 3 Order migrations, actual Account-target refusal and HTTP CRUD; historical/deleted/nonexistent account semantics; no FK")
}
