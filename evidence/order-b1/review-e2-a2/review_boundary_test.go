// Review-only overlay tests. All database resources are fresh disposable fixtures.
package orderpostgres

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"gitlab.com/platform-engineering-lab/backend-app/internal/order"
	"gitlab.com/platform-engineering-lab/backend-app/internal/orderhttp"
	"gitlab.com/platform-engineering-lab/backend-app/internal/ordertest"
)

func TestReviewBoundedPoolFailureAndRecovery(t *testing.T) {
	d := ordertest.Start(t, "orders", "order_app")
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	s, err := Open(ctx, d.URL())
	if err != nil {
		t.Fatal("open")
	}
	defer s.Close()
	if s.Migrate(ctx) != nil {
		t.Fatal("migrate")
	}
	api := httptest.NewServer(orderhttp.New(order.New(s), s))
	defer api.Close()
	client := &http.Client{Timeout: 7 * time.Second}
	call := func(method, path, body string, want int, max time.Duration) []byte {
		t.Helper()
		req, _ := http.NewRequest(method, api.URL+path, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		started := time.Now()
		res, e := client.Do(req)
		if e != nil {
			t.Fatal("transport")
		}
		defer res.Body.Close()
		raw, e := io.ReadAll(res.Body)
		if e != nil || res.StatusCode != want || time.Since(started) > max {
			t.Fatalf("bounded HTTP want %d got %d", want, res.StatusCode)
		}
		if want >= 400 {
			var envelope struct {
				Error struct{ Code, Message string }
			}
			if json.Unmarshal(raw, &envelope) != nil || envelope.Error.Code == "" {
				t.Fatal("error envelope")
			}
			for _, word := range []string{"order_app", "postgres", "public.orders", "SELECT", "INSERT", "password"} {
				if strings.Contains(string(raw), word) {
					t.Fatal("private error leak")
				}
			}
		}
		return raw
	}
	var held []*pgxpool.Conn
	defer func() {
		for _, c := range held {
			c.Release()
		}
	}()
	for i := 0; i < 5; i++ {
		c, e := s.pool.Acquire(ctx)
		if e != nil {
			t.Fatal("pool hold")
		}
		held = append(held, c)
	}
	call("GET", "/readyz", "", 503, 2*time.Second)
	call("GET", "/livez", "", 200, time.Second)
	call("GET", "/api/orders/1", "", 503, 4*time.Second)
	call("POST", "/api/orders", `{"account_id":1,"item_code":"Blocked","quantity":1}`, 503, 4*time.Second)
	for _, c := range held {
		c.Release()
	}
	held = nil
	var n int
	if s.pool.QueryRow(ctx, `SELECT count(*) FROM public.orders`).Scan(&n) != nil || n != 0 {
		t.Fatal("failed HTTP committed a row")
	}
	call("GET", "/readyz", "", 200, time.Second)
	raw := call("POST", "/api/orders", `{"account_id":1,"item_code":"Recovered","quantity":1}`, 201, time.Second)
	var item order.Order
	if json.Unmarshal(raw, &item) != nil || item.ID < 1 || item.CreatedAt.Location() != time.UTC {
		t.Fatal("positive UTC response")
	}
	// Real SQL schema error must be sanitized as 500, not a false 201 or 404.
	if _, e := s.pool.Exec(ctx, `ALTER TABLE public.orders RENAME TO review_hidden_orders`); e != nil {
		t.Fatal("test fixture rename")
	}
	call("GET", "/api/orders/1", "", 500, time.Second)
	call("POST", "/api/orders", `{"account_id":1,"item_code":"Hidden","quantity":1}`, 500, time.Second)
	if _, e := s.pool.Exec(ctx, `ALTER TABLE public.review_hidden_orders RENAME TO orders`); e != nil {
		t.Fatal("test fixture restore")
	}
	call("GET", "/api/orders/1", "", 200, time.Second)
	t.Log("five occupied connections: readiness and read/create deadlines return sanitized 503 within 2s/4s test tolerances; livez remains 200; zero writes; pool recovers; real missing-table failures return sanitized 500 and recover")
}
